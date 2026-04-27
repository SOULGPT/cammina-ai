import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from database import PROJECTS_DIR, get_db
import working_memory
import vector_memory
import graph_memory
import checkpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ChromaDB initializes synchronously, SQLite connects on demand.
    logger.info("Cammina Memory System started.")
    yield
    logger.info("Cammina Memory System shutting down.")

app = FastAPI(
    title="Cammina Memory System",
    description="Handles memory and context persistence for Cammina AI.",
    lifespan=lifespan
)

# --- Models ---

class ProjectInitRequest(BaseModel):
    project_id: str
    project_name: str

class MemorySaveRequest(BaseModel):
    project_id: Optional[str] = None
    project_name: str
    content: str
    memory_type: str # 'action', 'task_summary', etc.
    is_explicit: bool = False

class MemorySearchRequest(BaseModel):
    query: str
    project_name: str
    limit: int = 5

class CheckpointSaveRequest(BaseModel):
    task_id: str
    current_step: int
    messages: list[dict]
    files_modified: list[str]
    commands_run: list[str]
    next_action: str

class CheckpointLoadRequest(BaseModel):
    task_id: str

class SkillsSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

class SkillsSaveRequest(BaseModel):
    name: str
    category: str
    description: str
    learned_from_project: str

# --- Endpoints ---

@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "healthy", 
        "service": "cammina-memory"
    }

@app.post("/project/init", tags=["project"])
async def project_init(req: ProjectInitRequest):
    """
    Creates project folder structure, initializes collection, and saves metadata.
    """
    try:
        proj_dir = PROJECTS_DIR / req.project_name
        subfolders = ["memory", "errors", "task_logs", "console_logs"]
        
        for folder in subfolders:
            os.makedirs(proj_dir / folder, exist_ok=True)
            
        vector_memory.init_project_collection(req.project_name)
        
        # Save to SQLite
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO projects (id, name, folder_path) VALUES (?, ?, ?)",
                (req.project_id, req.project_name, str(proj_dir))
            )
            conn.commit()
            
        return {
            "success": True,
            "folder_path": str(proj_dir)
        }
    except Exception as e:
        logger.error(f"Error initializing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def save_to_file(project_name, content, memory_type):
    folder = PROJECTS_DIR / project_name / "memory"
    os.makedirs(folder, exist_ok=True)
    file_path = folder / "actions.json"
    
    actions = []
    if os.path.exists(file_path):
        try:
            with open(file_path) as f:
                actions = json.load(f)
        except:
            actions = []
    
    actions.append({
        "content": content,
        "memory_type": memory_type,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(file_path, 'w') as f:
        json.dump(actions, f, indent=2)

def is_meaningful_memory(content: str) -> bool:
    if len(content) < 30: return False
    skip_prefixes = ["Step ", "Starting step", "Completed task:", "step_result", "Task complete", "Executing:"]
    for p in skip_prefixes:
        if content.startswith(p): return False
    
    meaningful = ["created", "built", "deployed", "installed", "fixed", "configured", "pushed", "cloned", "wrote", "/Users/", "http", "successfully", "project", "app", "file"]
    content_lower = content.lower()
    return any(kw in content_lower for kw in meaningful)

@app.post("/memory/save", tags=["memory"])
async def memory_save(req: MemorySaveRequest):
    """
    Saves content to vector DB and appends to local actions log.
    """
    try:
        # Filter if not explicit
        if not req.is_explicit and not is_meaningful_memory(req.content):
            return {"success": True, "status": "skipped_not_meaningful"}

        # 1. Save to vector memory
        vector_memory.save_vector_memory(req.project_name, req.content, {"type": req.memory_type})
        
        # 2. Append to actions.json properly
        save_to_file(req.project_name, req.content, req.memory_type)
            
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search", tags=["memory"])
async def memory_search(req: MemorySearchRequest):
    try:
        results = vector_memory.search_vector_memory(req.project_name, req.query, req.limit)
        return {
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects", tags=["project"])
async def get_projects_list():
    """
    Lists all projects with metadata from directory structure.
    """
    projects = []
    if os.path.exists(PROJECTS_DIR):
        for name in os.listdir(PROJECTS_DIR):
            proj_path = PROJECTS_DIR / name
            if os.path.isdir(proj_path):
                actions_file = proj_path / "memory" / "actions.json"
                task_count = 0
                last_active = ""
                
                if os.path.exists(actions_file):
                    try:
                        with open(actions_file, "r") as f:
                            actions = json.load(f)
                            task_count = len(actions)
                            if actions:
                                last_active = actions[-1].get("timestamp", "")
                    except:
                        pass
                
                projects.append({
                    "name": name,
                    "task_count": task_count,
                    "last_active": last_active,
                    "created": datetime.fromtimestamp(os.path.getctime(proj_path)).isoformat()
                })
    return {"projects": projects}

@app.post("/checkpoint/save", tags=["checkpoint"])
async def checkpoint_save(req: CheckpointSaveRequest):
    try:
        cp_id = checkpoint.save_checkpoint(
            task_id=req.task_id,
            current_step=req.current_step,
            messages=req.messages,
            files_modified=req.files_modified,
            commands_run=req.commands_run,
            next_action=req.next_action
        )
        return {"success": True, "checkpoint_id": cp_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/checkpoint/load", tags=["checkpoint"])
async def checkpoint_load(req: CheckpointLoadRequest):
    data = checkpoint.load_checkpoint(req.task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return data

@app.post("/skills/search", tags=["skills"])
async def skills_search(req: SkillsSearchRequest):
    results = graph_memory.search_skills(req.query, req.category)
    return {"skills": results}

@app.post("/skills/save", tags=["skills"])
async def skills_save(req: SkillsSaveRequest):
    success = graph_memory.save_skill(req.name, req.category, req.description, req.learned_from_project)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to save skill.")
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
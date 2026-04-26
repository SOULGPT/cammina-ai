import json
import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from database import PROJECTS_DIR
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
    description="Handles memory and context persistence.",
    lifespan=lifespan
)

# --- Models ---

class MemorySaveRequest(BaseModel):
    task_id: str
    project_id: str
    content: str
    memory_type: str # 'working', 'project', etc.

class MemorySearchRequest(BaseModel):
    query: str
    project_id: str
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

class ProjectInitRequest(BaseModel):
    project_id: str
    project_name: str

# --- Endpoints ---

@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "healthy", 
        "service": "cammina-memory"
    }

@app.post("/memory/save", tags=["memory"])
async def memory_save(req: MemorySaveRequest):
    try:
        if req.memory_type == "working":
            working_memory.save_working_memory(req.task_id, req.project_id, req.content)
        elif req.memory_type == "project":
            vector_memory.save_vector_memory(req.project_id, req.content, {"task_id": req.task_id})
        else:
            raise HTTPException(status_code=400, detail=f"Unknown memory type: {req.memory_type}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search", tags=["memory"])
async def memory_search(req: MemorySearchRequest):
    try:
        results = vector_memory.search_vector_memory(req.project_id, req.query, req.limit)
        return {
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return {
            "success": True,
            "checkpoint_id": cp_id
        }
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
        raise HTTPException(status_code=400, detail="Failed to save skill. Name might already exist.")
    return {"success": True}

@app.post("/project/init", tags=["project"])
async def project_init(req: ProjectInitRequest):
    """
    Creates project folder structure and initializes ChromaDB collection.
    Subfolders: memory/, errors/, task_logs/, console_logs/
    """
    try:
        proj_dir = PROJECTS_DIR / req.project_name
        subfolders = ["memory", "errors", "task_logs", "console_logs"]
        
        for folder in subfolders:
            os.makedirs(proj_dir / folder, exist_ok=True)
            
        vector_memory.init_project_collection(req.project_id)
        
        return {
            "success": True,
            "folder_path": str(proj_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 8002 as specified by prompt
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
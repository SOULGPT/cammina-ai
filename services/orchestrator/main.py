import uuid
import logging
import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import planner
import task_manager
import agent
from config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cammina Orchestrator",
    description="The brain coordinating Cammina AI."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class TaskStartRequest(BaseModel):
    task: str
    project_id: str
    project_name: str

class TaskAnswerRequest(BaseModel):
    task_id: str
    task: str
    answers: dict

class TaskActionRequest(BaseModel):
    task_id: str


# --- Endpoints ---

@app.get("/health", tags=["system"])
async def health():
    return {"status": "healthy", "service": "cammina-orchestrator"}

@app.get("/user/home")
async def get_user_home():
    import os
    return {
        "home": os.path.expanduser("~"),
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "username": os.path.basename(os.path.expanduser("~"))
    }


@app.post("/task/start", tags=["task"])
async def task_start(req: TaskStartRequest):
    task_id = str(uuid.uuid4())
    state = task_manager.get_state(task_id)
    state["project_id"] = req.project_id
    state["task_description"] = req.task
    
    questions = await planner.ask_clarifying_questions(req.task, task_id)
    
    return {
        "task_id": task_id,
        "questions": questions
    }

@app.post("/task/answer", tags=["task"])
async def task_answer(req: TaskAnswerRequest):
    plan = await planner.create_plan(req.task, req.answers, req.task_id)
    
    state = task_manager.get_state(req.task_id)
    state["plan"] = plan
    state["total_steps"] = len(plan)
    state["task_description"] = req.task
    
    return {
        "task_id": req.task_id,
        "plan": plan,
        "estimated_steps": len(plan)
    }

@app.post("/task/execute", tags=["task"])
async def task_execute(req: TaskActionRequest, background_tasks: BackgroundTasks):
    state = task_manager.get_state(req.task_id)
    if not state["plan"]:
        raise HTTPException(status_code=400, detail="No plan found. Call /task/answer first.")
        
    started = task_manager.start_execution(req.task_id)
    if not started:
        raise HTTPException(status_code=400, detail="Task is already running.")
        
    return {"task_id": req.task_id, "status": "running"}

@app.post("/task/pause", tags=["task"])
async def task_pause(req: TaskActionRequest):
    paused = task_manager.pause_execution(req.task_id)
    return {"success": paused}

@app.post("/task/resume", tags=["task"])
async def task_resume(req: TaskActionRequest):
    started = task_manager.start_execution(req.task_id)
    return {"success": started}


@app.get("/task/status/{task_id}", tags=["task"])
async def task_status(task_id: str):
    state = task_manager.get_state(task_id)
    return {
        "status": state["status"],
        "current_step": state["current_step"],
        "total_steps": state["total_steps"],
        "errors_count": state["errors_count"]
    }

@app.websocket("/task/stream/{task_id}")
async def task_stream(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in task_manager.active_websockets:
        task_manager.active_websockets[task_id] = []
    task_manager.active_websockets[task_id].append(websocket)
    
    try:
        # Keep connection open
        while True:
            data = await websocket.receive_text()
            # Handle any incoming commands from client if needed later
    except WebSocketDisconnect:
        if websocket in task_manager.active_websockets.get(task_id, []):
            task_manager.active_websockets[task_id].remove(websocket)


@app.post("/cursor/autonomous")
async def cursor_autonomous(request: dict):
    import httpx, os, asyncio, re
    from config import settings
    
    instruction = request.get("instruction", "")
    max_rounds = request.get("max_rounds", 5)
    home = settings.user_home
    
    agent_url = settings.agent_url
    agent_secret = settings.local_agent_secret
    if not agent_secret:
        raise HTTPException(status_code=500, detail="LOCAL_AGENT_SECRET not configured. Check .env.local")
    
    headers = {"Authorization": f"Bearer {agent_secret}"}
    
    results = []
    commands_run = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # --- MEMORY START ---
        project_name = request.get("project_name", "general")
        project_id = request.get("project_id", str(uuid.uuid4()))
        
        await client.post(f"{settings.memory_url}/project/init", json={
            "project_id": project_id,
            "project_name": project_name
        })
        
        # Search for context
        mem_search = await client.post(f"{settings.memory_url}/memory/search", json={
            "query": instruction,
            "project_name": project_name,
            "limit": 3
        })
        mem_results = mem_search.json().get("results", [])
        if mem_results:
            context_note = f"\n\nPrevious context: {mem_results[0].get('content')}"
            instruction += context_note
        # --- MEMORY END ---

        # 1. Snapshot home directory (files AND dirs)
        before_scan = set()
        # ... rest of snapshots ...
        # (skipping for brevity but keeping logic)
        
        # [Existing snapshot logic]
        before_dirs = set()
        for root, dirs, files in os.walk(home):
            depth = root.replace(home, '').count(os.sep)
            if depth < 3:
                for f in files: before_scan.add(os.path.join(root, f))
                for d in dirs: before_dirs.add(os.path.join(root, d))
            else: dirs.clear()
        
        # 2. Type instruction
        await client.post(f"{agent_url}/cursor/type", headers=headers, json={"text": instruction})
        results.append("Sent instruction to Cursor")
        
        # 3. Wait for Cursor
        await asyncio.sleep(12)
        
        # 4. Read Chat
        # ... [Existing read chat logic] ...
        try:
            chat_resp = await client.post(f"{agent_url}/cursor/read_chat", headers=headers)
            chat_text = chat_resp.json().get("text", "")
            results.append(f"Cursor chat read successfully.")
        except Exception as e:
            chat_text = ""; results.append(f"Failed to read chat: {str(e)}")
        
        # 5. Detect New Files & Dirs
        new_files = []; new_dirs = []
        for root, dirs, files in os.walk(home):
            depth = root.replace(home, '').count(os.sep)
            if depth < 3:
                for f in files:
                    full_f = os.path.join(root, f)
                    if full_f not in before_scan: new_files.append(full_f)
                for d in dirs:
                    full_d = os.path.join(root, d)
                    if full_d not in before_dirs: new_dirs.append(full_d)
            else: dirs.clear()
        
        results.append(f"New files: {len(new_files)}, New dirs: {len(new_dirs)}")
        
        # 6. Extract Commands
        # ... [Existing extraction logic] ...
        code_blocks = re.findall(r'```(?:bash|sh|shell)?\n?(.*?)```', chat_text, re.DOTALL)
        extracted_commands = []
        for block in code_blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'): extracted_commands.append(line)
        for line in chat_text.split('\n'):
            line = line.strip()
            if line.startswith(('npm ', 'pip ', 'python3 ', 'node ', 'yarn ', 'cd ')):
                if line not in extracted_commands: extracted_commands.append(line)
        
        # 7. Execute Commands
        project_path = home
        if new_dirs:
            new_dirs.sort(key=len); project_path = new_dirs[0]
            results.append(f"Detected project path: {project_path}")

        for cmd in extracted_commands[:10]:
            try:
                cmd_resp = await client.post(f"{agent_url}/terminal", headers=headers, json={"command": cmd, "cwd": project_path})
                cmd_result = cmd_resp.json(); stdout = cmd_result.get("stdout", "")
                commands_run.append({"command": cmd, "stdout": stdout[:200]})
                results.append(f"Ran '{cmd}'")
                
                # SAVE TO MEMORY
                await client.post(f"{settings.memory_url}/memory/save", json={
                    "project_name": project_name,
                    "content": f"Ran command '{cmd}' in {project_path}. Output snippet: {stdout[:100]}",
                    "memory_type": "action"
                })
                await asyncio.sleep(1)
            except Exception as e:
                results.append(f"Failed '{cmd}': {str(e)}")
        
        # 8. Post-Execution Auto-Installs
        # ... [Existing install logic] ...
        for d in new_dirs:
            if os.path.exists(os.path.join(d, 'package.json')):
                try:
                    await client.post(f"{agent_url}/terminal", headers=headers, json={"command": "npm install", "cwd": d})
                    results.append(f"Auto-ran npm install in {d}")
                    commands_run.append({"command": "npm install", "stdout": "Success"})
                    await client.post(f"{settings.memory_url}/memory/save", json={
                        "project_name": project_name,
                        "content": f"Auto-ran npm install in {d}",
                        "memory_type": "action"
                    })
                except: pass

        # --- MEMORY FINAL ---
        await client.post(f"{settings.memory_url}/memory/save", json={
            "project_name": project_name,
            "content": f"Completed autonomous Cursor task: {instruction[:100]}. Created {len(new_files)} files.",
            "memory_type": "task_summary"
        })
        # --- MEMORY FINAL END ---
    
    return {
        "success": True,
        "rounds": 1,
        "commands_run": commands_run,
        "new_files": new_files,
        "new_dirs": new_dirs,
        "project_path": project_path,
        "results": results,
        "chat_text": chat_text[:500]
    }

@app.get("/projects")
async def get_projects():
    import os, json
    projects_dir = "../../logs/projects"
    projects = []
    
    if os.path.exists(projects_dir):
        for name in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, name)
            if os.path.isdir(project_path):
                # Count memories
                memory_count = 0
                actions_file = os.path.join(project_path, "memory", "actions.json")
                if os.path.exists(actions_file):
                    try:
                        with open(actions_file) as f:
                            actions = json.load(f)
                            memory_count = len(actions)
                    except: pass
                
                projects.append({
                    "name": name,
                    "memory_count": memory_count,
                    "path": project_path
                })
    
    # Sort by name
    projects.sort(key=lambda x: x["name"])
    return {"projects": projects}

@app.post("/projects/create")
async def create_project(request: dict):
    import os
    name = request.get("name")
    if not name: return {"error": "Name required"}
    
    base_path = f"../../logs/projects/{name}"
    os.makedirs(f"{base_path}/memory", exist_ok=True)
    os.makedirs(f"{base_path}/logs", exist_ok=True)
    os.makedirs(f"{base_path}/errors", exist_ok=True)
    os.makedirs(f"{base_path}/task_logs", exist_ok=True)
    
    return {"success": True, "name": name}

@app.get("/projects/{project_name}")
async def get_project_details(project_name: str):
    import os, json, time
    project_path = f"../../logs/projects/{project_name}"
    if not os.path.exists(project_path):
        return {"error": "Project not found"}
    
    memories = []
    actions_file = os.path.join(project_path, "memory", "actions.json")
    if os.path.exists(actions_file):
        try:
            with open(actions_file) as f: memories = json.load(f)
        except: pass
    
    files = []
    search_paths = [
        os.path.expanduser(f"~/Desktop/{project_name}"),
        os.path.expanduser(f"~/Documents/{project_name}")
    ]
    for path in search_paths:
        if os.path.exists(path):
            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    if f.startswith('.'): continue
                    full_path = os.path.join(root, f)
                    stats = os.stat(full_path)
                    files.append({
                        "name": f,
                        "path": full_path,
                        "size": stats.st_size,
                        "modified": time.ctime(stats.st_mtime)
                    })
    
    tasks = [m for m in memories if m.get("memory_type") == "task_summary"]
    
    return {
        "name": project_name,
        "created_at": time.ctime(os.path.getctime(project_path)),
        "memory_count": len(memories),
        "memories": memories[::-1],
        "files": files,
        "tasks": tasks[::-1]
    }

@app.get("/projects/{project_name}/memories")
async def get_project_memories(project_name: str):
    import os, json
    file_path = f"../../logs/projects/{project_name}/memory/actions.json"
    if not os.path.exists(file_path): return {"memories": []}
    try:
        with open(file_path) as f:
            actions = json.load(f)
            return {"memories": actions[::-1]}
    except: return {"error": "Failed to read memories"}

@app.post("/projects/{project_name}/memories")
async def add_project_memory(project_name: str, request: dict):
    import os, json, datetime, uuid
    file_path = f"../../logs/projects/{project_name}/memory/actions.json"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    actions = []
    if os.path.exists(file_path):
        try:
            with open(file_path) as f: actions = json.load(f)
        except: pass
    
    new_memory = {
        "id": str(uuid.uuid4()),
        "content": request.get("content"),
        "memory_type": request.get("memory_type", "user_note"),
        "timestamp": datetime.datetime.now().isoformat()
    }
    actions.append(new_memory)
    
    with open(file_path, 'w') as f: json.dump(actions, f, indent=2)
    return {"success": True, "memories": actions[::-1]}

@app.delete("/projects/{project_name}/memories/{index}")
async def delete_project_memory(project_name: str, index: int):
    import os, json
    file_path = f"../../logs/projects/{project_name}/memory/actions.json"
    if not os.path.exists(file_path): return {"error": "No memory file"}
    
    try:
        with open(file_path) as f: actions = json.load(f)
        if 0 <= index < len(actions):
            actions.pop(index)
            with open(file_path, 'w') as f: json.dump(actions, f, indent=2)
            return {"success": True, "memories": actions[::-1]}
        return {"error": "Invalid index"}
    except Exception as e: return {"error": str(e)}

@app.delete("/projects/{project_name}")
async def delete_project(project_name: str):
    import shutil, os
    project_path = f"../../logs/projects/{project_name}"
    if os.path.exists(project_path):
        shutil.rmtree(project_path)
        return {"success": True}
    return {"error": "Project not found"}

@app.post("/memory/cleanup")
async def cleanup_memory(request: dict):
    import json, os
    project_name = request.get("project_name", "general")
    file_path = f"../../logs/projects/{project_name}/memory/actions.json"
    
    if not os.path.exists(file_path):
        return {"success": True, "deleted": 0, "message": "No memory file found"}
    
    try:
        with open(file_path) as f:
            actions = json.load(f)
        
        bad_prefixes = ["Step ", "Starting step", "Completed task:", "step_result", "Task complete", "Executing:", "checkpoint", "provider switched"]
        good_actions = []
        deleted = 0
        for action in actions:
            content = action.get("content", "")
            is_bad = any(content.startswith(p) for p in bad_prefixes)
            is_too_short = len(content) < 30
            if is_bad or is_too_short:
                deleted += 1
            else:
                good_actions.append(action)
        
        with open(file_path, 'w') as f:
            json.dump(good_actions, f, indent=2)
        
        return {"success": True, "deleted": deleted, "remaining": len(good_actions)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/memory/cleanup-all")
async def cleanup_all_memory():
    import json, os
    projects_dir = "../../logs/projects"
    total_deleted = 0
    if not os.path.exists(projects_dir):
        return {"success": True, "deleted": 0}
    
    bad_prefixes = ["Step ", "Starting step", "Completed task:", "step_result", "Task complete", "Executing:", "checkpoint", "provider switched"]
    
    for project_name in os.listdir(projects_dir):
        file_path = f"{projects_dir}/{project_name}/memory/actions.json"
        if not os.path.exists(file_path): continue
        try:
            with open(file_path) as f:
                actions = json.load(f)
            good = [a for a in actions if not any(a.get("content","").startswith(p) for p in bad_prefixes) and len(a.get("content","")) >= 30]
            total_deleted += len(actions) - len(good)
            with open(file_path, 'w') as f:
                json.dump(good, f, indent=2)
        except: pass
    
    return {"success": True, "deleted": total_deleted}

@app.post("/task/quick")
async def task_quick(request: dict):
    import httpx, os
    from config import settings
    action = request.get("action")
    url = settings.agent_url
    secret = settings.local_agent_secret
    if not secret:
        raise HTTPException(status_code=500, detail="LOCAL_AGENT_SECRET not configured. Check .env.local")
    headers = {"Authorization": f"Bearer {secret}"}
    
    # Optional: Save note to memory
    if action == "remember":
        project_name = request.get("project_name", "general")
        content = request.get("note", "")
        async with httpx.AsyncClient() as c:
            await c.post(f"{settings.memory_url}/memory/save", json={
                "project_name": project_name,
                "content": content,
                "memory_type": "note",
                "is_explicit": True
            })
        return {"success": True, "message": "Memory saved"}

    try:
        if action == "file_write":
            async with httpx.AsyncClient() as c:
                await c.post(f"{url}/file/write", headers=headers, json={"path": request.get("path"), "content": request.get("content")})
            return {"success": True, "message": f"File created at {request.get('path')}"}
        elif action == "terminal":
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{url}/terminal", headers=headers, json={"command": request.get("command"), "cwd": request.get("cwd", settings.user_home)})
            return r.json()
        elif action == "file_read":
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{url}/file/read", headers=headers, json={"path": request.get("path")})
            return r.json()
        elif action == "screenshot":
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(f"{url}/browser/screenshot", headers=headers)
            return r.json()
        elif action == "app_open":
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(f"{url}/app/open", headers=headers, json={"app_name": request.get("app", "Cursor")})
            return r.json()
        elif action == "cursor_type":
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(f"{url}/cursor/type", headers=headers, json={"text": request.get("text", "")})
            return r.json()
        elif action == "cursor_type_antigravity":
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(f"{url}/cursor/type_antigravity", headers=headers, json={"text": request.get("text", "")})
            return r.json()
        elif action == "cursor_focus":
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(f"{url}/cursor/focus", headers=headers, json={"app": request.get("app", "Cursor")})
            return r.json()
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.orchestrator_host, port=settings.orchestrator_port, reload=True)


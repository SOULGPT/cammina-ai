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
    home = "/Users/miruzaankhan"
    
    agent_url = settings.agent_url
    agent_secret = settings.local_agent_secret or "mezZeq2aZz6gh8U4emyvd5AhqnsUW6buq/3T4uvZwkM="
    headers = {"Authorization": f"Bearer {agent_secret}"}
    
    results = []
    commands_run = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # 1. Snapshot home directory (files AND dirs)
        before_scan = set()
        before_dirs = set()
        for root, dirs, files in os.walk(home):
            depth = root.replace(home, '').count(os.sep)
            if depth < 3:
                for f in files:
                    before_scan.add(os.path.join(root, f))
                for d in dirs:
                    before_dirs.add(os.path.join(root, d))
            else:
                dirs.clear()
        
        # 2. Type instruction
        await client.post(f"{agent_url}/cursor/type",
            headers=headers,
            json={"text": instruction})
        results.append("Sent instruction to Cursor")
        
        # 3. Wait for Cursor
        await asyncio.sleep(12)
        
        # 4. Read Chat
        try:
            chat_resp = await client.post(
                f"{agent_url}/cursor/read_chat",
                headers=headers
            )
            chat_text = chat_resp.json().get("text", "")
            results.append(f"Cursor chat read successfully.")
        except Exception as e:
            chat_text = ""
            results.append(f"Failed to read chat: {str(e)}")
        
        # 5. Detect New Files & Dirs
        new_files = []
        new_dirs = []
        for root, dirs, files in os.walk(home):
            depth = root.replace(home, '').count(os.sep)
            if depth < 3:
                for f in files:
                    full_f = os.path.join(root, f)
                    if full_f not in before_scan:
                        new_files.append(full_f)
                for d in dirs:
                    full_d = os.path.join(root, d)
                    if full_d not in before_dirs:
                        new_dirs.append(full_d)
            else:
                dirs.clear()
        
        results.append(f"New files: {len(new_files)}, New dirs: {len(new_dirs)}")
        
        # 6. Extract Commands
        code_blocks = re.findall(r'```(?:bash|sh|shell)?\n?(.*?)```',
                                  chat_text, re.DOTALL)
        extracted_commands = []
        for block in code_blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    extracted_commands.append(line)
        
        for line in chat_text.split('\n'):
            line = line.strip()
            if line.startswith(('npm ', 'pip ', 'python3 ',
                                  'node ', 'yarn ', 'cd ')):
                if line not in extracted_commands:
                    extracted_commands.append(line)
        
        # 7. Execute Commands (Try to find project path from new_dirs)
        project_path = home
        if new_dirs:
            # Sort by length, shortest is likely the root of the new project
            new_dirs.sort(key=len)
            project_path = new_dirs[0]
            results.append(f"Detected project path: {project_path}")

        for cmd in extracted_commands[:10]:
            try:
                cmd_resp = await client.post(
                    f"{agent_url}/terminal",
                    headers=headers,
                    json={"command": cmd, "cwd": project_path}
                )
                cmd_result = cmd_resp.json()
                stdout = cmd_result.get("stdout", "")
                commands_run.append({"command": cmd, "stdout": stdout[:200]})
                results.append(f"Ran '{cmd}'")
                await asyncio.sleep(1)
            except Exception as e:
                results.append(f"Failed '{cmd}': {str(e)}")
        
        # 8. Post-Execution Auto-Installs in new project path
        for d in new_dirs:
            if os.path.exists(os.path.join(d, 'package.json')):
                try:
                    await client.post(f"{agent_url}/terminal",
                        headers=headers,
                        json={"command": "npm install", "cwd": d})
                    results.append(f"Auto-ran npm install in {d}")
                    commands_run.append({"command": "npm install", "stdout": "Success"})
                except: pass
            if os.path.exists(os.path.join(d, 'requirements.txt')):
                try:
                    await client.post(f"{agent_url}/terminal",
                        headers=headers,
                        json={"command": "pip3 install -r requirements.txt", "cwd": d})
                    results.append(f"Auto-ran pip install in {d}")
                    commands_run.append({"command": "pip3 install", "stdout": "Success"})
                except: pass
    
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

@app.post("/task/quick")
async def task_quick(request: dict):
    import httpx, os
    from config import settings
    action = request.get("action")
    url = settings.agent_url
    secret = settings.local_agent_secret or "mezZeq2aZz6gh8U4emyvd5AhqnsUW6buq/3T4uvZwkM="
    headers = {"Authorization": f"Bearer {secret}"}
    try:
        if action == "file_write":
            async with httpx.AsyncClient() as c:
                await c.post(f"{url}/file/write", headers=headers, json={"path": request.get("path"), "content": request.get("content")})
            return {"success": True, "message": f"File created at {request.get('path')}"}
        elif action == "terminal":
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{url}/terminal", headers=headers, json={"command": request.get("command"), "cwd": request.get("cwd", "/Users/miruzaankhan")})
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


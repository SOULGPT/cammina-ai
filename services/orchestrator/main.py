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


@app.post("/cursor/autonomous", tags=["cursor"])
async def cursor_autonomous(request: dict):
    """
    Run an autonomous loop with Cursor.
    """
    instruction = request.get("instruction")
    project_path = request.get("project_path", "/Users/miruzaankhan/Desktop")
    max_rounds = request.get("max_rounds", 10)
    
    task_id = str(uuid.uuid4())
    result = await task_manager.execute_autonomous_cursor(task_id, instruction, project_path, max_rounds)
    return result

@app.post("/task/quick")
async def task_quick(request: dict):
    import httpx, os
    action = request.get("action")
    url = "http://localhost:8765"
    secret = os.getenv("LOCAL_AGENT_SECRET", "mezZeq2aZz6gh8U4emyvd5AhqnsUW6buq/3T4uvZwkM=")
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


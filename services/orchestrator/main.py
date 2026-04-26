import uuid
import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import planner
import task_manager
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
    allow_credentials=True,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.orchestrator_host, port=settings.orchestrator_port, reload=True)

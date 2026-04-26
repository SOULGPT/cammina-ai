import asyncio
import json
import logging
import httpx
from datetime import datetime, timezone

import planner
import agent
import error_handler
from config import settings

logger = logging.getLogger(__name__)

# In-memory storage for active tasks and WebSocket connections
active_tasks: dict[str, asyncio.Task] = {}
task_states: dict[str, dict] = {}
active_websockets: dict[str, list] = {}

def get_state(task_id: str) -> dict:
    if task_id not in task_states:
        task_states[task_id] = {
            "status": "pending",
            "current_step": 0,
            "plan": [],
            "history": [],
            "errors_count": 0,
            "total_steps": 0,
            "project_id": "unknown"
        }
    return task_states[task_id]

async def broadcast_event(task_id: str, event_type: str, data: dict):
    """Send event to all connected WebSockets for this task."""
    if task_id in active_websockets:
        message = json.dumps({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data
        })
        # Iterate over a copy to handle disconnections during broadcast
        for ws in list(active_websockets[task_id]):
            try:
                await ws.send_text(message)
            except Exception:
                active_websockets[task_id].remove(ws)

async def _save_checkpoint(task_id: str):
    """Save the current state to the memory service."""
    state = get_state(task_id)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{settings.memory_url}/checkpoint/save", json={
                "task_id": task_id,
                "current_step": state["current_step"],
                "messages": state["history"],
                "files_modified": [], # Can be extracted from history later
                "commands_run": [],
                "next_action": "resume"
            })
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")

async def checkpoint_loop(task_id: str):
    """Runs continuously alongside the task to save checkpoints every 30s."""
    try:
        while True:
            await asyncio.sleep(30)
            await _save_checkpoint(task_id)
    except asyncio.CancelledError:
        # Save one final time when paused/cancelled
        await _save_checkpoint(task_id)

async def execute_task_loop(task_id: str):
    """The autonomous execution loop."""
    state = get_state(task_id)
    state["status"] = "running"
    
    # Start the checkpoint loop
    cp_task = asyncio.create_task(checkpoint_loop(task_id))
    
    try:
        plan = state["plan"]
        
        while state["current_step"] < len(plan):
            step = plan[state["current_step"]]
            await broadcast_event(task_id, "step_start", {"step": step})
            
            retry_count = 0
            success = False
            action_to_take = None
            
            while retry_count < 10 and not success:
                if retry_count == 0:
                    action_to_take = await planner.decide_next_command(step, state["history"], task_id)
                else:
                    await broadcast_event(task_id, "retrying", {"attempt": retry_count})
                
                if not action_to_take:
                    retry_count += 1
                    continue
                
                await broadcast_event(task_id, "action", {"action": action_to_take})
                
                # Execute action
                result = {}
                if "command" in action_to_take:
                    result = await agent.run_terminal(action_to_take["command"], action_to_take.get("cwd"))
                elif "file_path" in action_to_take and "content" in action_to_take:
                    result = await agent.file_write(action_to_take["file_path"], action_to_take["content"])
                elif "file_path" in action_to_take:
                    result = await agent.file_read(action_to_take["file_path"])
                else:
                    result = {"error": "Unknown action format"}
                
                await broadcast_event(task_id, "result", {"result": result})
                state["history"].append({"action": action_to_take, "result": result})
                
                # Check for success
                is_error = result.get("error") or (result.get("exit_code", 0) != 0)
                if not is_error:
                    success = True
                else:
                    state["errors_count"] += 1
                    retry_count += 1
                    if retry_count < 10:
                        action_to_take = await error_handler.handle_error(step, action_to_take, result, state["history"], task_id)
            
            if not success:
                # Max retries reached
                state["status"] = "paused_error"
                await broadcast_event(task_id, "error_limit_reached", {
                    "message": "Step failed after 10 retries. Pausing for user input.",
                    "step": step
                })
                break # Exit loop
                
            # Step succeeded
            state["current_step"] += 1
            await _save_checkpoint(task_id)
            
        if state["current_step"] >= len(plan):
            state["status"] = "completed"
            await broadcast_event(task_id, "completed", {"message": "Task 100% complete"})
            
    except asyncio.CancelledError:
        state["status"] = "paused"
        await broadcast_event(task_id, "paused", {"message": "Task paused"})
    except Exception as e:
        logger.error(f"Fatal error in task loop: {e}")
        state["status"] = "error"
        state["errors_count"] += 1
        await broadcast_event(task_id, "fatal_error", {"error": str(e)})
    finally:
        cp_task.cancel()
        if task_id in active_tasks:
            del active_tasks[task_id]

def start_execution(task_id: str):
    """Start or resume the execution loop."""
    if task_id in active_tasks:
        return False # Already running
        
    task = asyncio.create_task(execute_task_loop(task_id))
    active_tasks[task_id] = task
    return True

def pause_execution(task_id: str):
    """Cancel the running task to pause it."""
    if task_id in active_tasks:
        active_tasks[task_id].cancel()
        return True
    return False
import asyncio
import json
import logging
import httpx
import re
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

async def try_direct_execution(task_id: str) -> bool:
    """Checks if the task can be handled without the LLM planner."""
    state = get_state(task_id)
    task_desc = state.get("task_description", "")
    if not task_desc:
        return False
        
    task_lower = task_desc.lower()
    
    # 1. File Write Handlers
    if any(k in task_lower for k in ["create a file", "write a file", "save a file", "make a file"]):
        # Use simpler regex as requested
        path_match = re.search(r'(?:at|to|named?)\s+([/~][^\s]+)', task_desc)
        content_match = re.search(r'(?:with content:|content:)\s*(.+?)$', task_desc, re.IGNORECASE | re.DOTALL)
        
        if path_match and content_match:
            path = path_match.group(1)
            content = content_match.group(1).strip().strip('"\'')
            await broadcast_event(task_id, "direct_execution", {"message": f"Directly writing to {path}"})
            result = await agent.file_write(path, content)
            await broadcast_event(task_id, "result", {"result": result})
            if not result.get("error"):
                state["status"] = "completed"
                await broadcast_event(task_id, "completed", {"message": "Direct task complete"})
                return True

    # 2. Terminal Handlers
    if "run this command:" in task_lower:
        cmd = task_desc.split("run this command:")[1].strip().strip('"\'')
        await broadcast_event(task_id, "direct_execution", {"message": f"Directly running command: {cmd}"})
        result = await agent.run_terminal(cmd)
        await broadcast_event(task_id, "result", {"result": result})
        state["status"] = "completed"
        await broadcast_event(task_id, "completed", {"message": "Direct task complete"})
        return True

    # 3. File Read Handlers
    if "read file at" in task_lower:
        path_match = re.search(r'read file at\s+([/~][^\s]+)', task_lower)
        if path_match:
            path = path_match.group(1)
            await broadcast_event(task_id, "direct_execution", {"message": f"Directly reading {path}"})
            result = await agent.file_read(path)
            await broadcast_event(task_id, "result", {"result": result})
            state["status"] = "completed"
            await broadcast_event(task_id, "completed", {"message": "Direct task complete"})
            return True
            
    return False

async def execute_task_loop(task_id: str):
    """The autonomous execution loop."""
    state = get_state(task_id)
    state["status"] = "running"
    
    # Start the checkpoint loop
    cp_task = asyncio.create_task(checkpoint_loop(task_id))
    
    try:
        # 0. Try direct execution first to bypass LLM
        if await try_direct_execution(task_id):
            return

        plan = state["plan"]
        
        while state["current_step"] < len(plan):
            step = plan[state["current_step"]]
            await broadcast_event(task_id, "step_start", {"step": step})
            
            retry_count = 0
            success = False
            action_to_take = None
            
            while retry_count < 50 and not success:
                if retry_count == 0:
                    # Compatibility fix: if the step already has action info (new planner format), use it!
                    if step.get("action_type") == "file_write" and step.get("file_path") and step.get("content"):
                        action_to_take = {
                            "file_path": step["file_path"],
                            "content": step["content"]
                        }
                    elif step.get("action_type") == "file_read" and step.get("file_path"):
                        action_to_take = {
                            "file_path": step["file_path"]
                        }
                    else:
                        # Fallback to old dynamic command decision
                        action_to_take = await planner.decide_next_command(step, state["history"], task_id)
                elif retry_count < 3:
                    # Retry same command for first 3 failures
                    await broadcast_event(task_id, "retrying", {"attempt": retry_count, "message": "Retrying same approach..."})
                    await asyncio.sleep(2)
                elif retry_count == 3 or (retry_count - 3) % 10 == 0:
                    # Switch approach after 3 failures, and every 10 failures after that
                    await broadcast_event(task_id, "retrying", {"attempt": retry_count, "message": "Asking LLM for alternative approach..."})
                    await asyncio.sleep(5)
                    action_to_take = await error_handler.handle_error(step, action_to_take, result, state["history"], task_id)
                else:
                    await broadcast_event(task_id, "retrying", {"attempt": retry_count, "message": "Retrying new approach..."})
                    await asyncio.sleep(2)
                
                if not action_to_take:
                    retry_count += 1
                    continue
                
                await broadcast_event(task_id, "action", {"action": action_to_take})
                
                # Safety check: never run rm/delete unless task asks for it
                if "command" in action_to_take:
                    cmd = action_to_take["command"].lower()
                    destructive_keywords = ["rm", "rmdir", "del", "delete"]
                    if any(k in cmd for k in destructive_keywords):
                        task_desc = state.get("task_description", "").lower()
                        if not any(word in task_desc for word in ["delete", "remove", "clean"]):
                            logger.warning(f"Skipped dangerous command: {cmd}")
                            await broadcast_event(task_id, "safety_skip", {"message": f"Skipped dangerous command: {cmd}"})
                            # Skip this step entirely as requested
                            success = True 
                            break # Break the retry loop, success=True moves to next step

                # Execute action
                result = {}
                try:
                    if "command" in action_to_take:
                        result = await agent.run_terminal(action_to_take["command"], action_to_take.get("cwd"))
                    elif "file_path" in action_to_take and "content" in action_to_take:
                        result = await agent.file_write(action_to_take["file_path"], action_to_take["content"])
                    elif "file_path" in action_to_take:
                        result = await agent.file_read(action_to_take["file_path"])
                    else:
                        result = {"error": "Unknown action format"}
                except Exception as e:
                    result = {"error": str(e)}
                
                await broadcast_event(task_id, "result", {"result": result})
                state["history"].append({"action": action_to_take, "result": result})
                
                # Check for success
                is_error = result.get("error") or (result.get("exit_code") is not None and result.get("exit_code") != 0)
                if not is_error:
                    success = True
                else:
                    state["errors_count"] += 1
                    retry_count += 1
            
            if not success:
                # Max retries reached
                state["status"] = "paused_error"
                await broadcast_event(task_id, "error_limit_reached", {
                    "message": "Step failed after 50 retries. Pausing for user input.",
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
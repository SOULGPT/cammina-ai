import asyncio
import json
import logging
import httpx
import re
import uuid
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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

async def execute_step(step: dict) -> dict:
    """Routes the step to the correct agent function based on action_type."""
    action_type = step.get("action_type")
    
    if action_type == "file_write":
        return await agent.file_write(step.get("file_path"), step.get("content", ""))
        
    elif action_type == "file_read":
        return await agent.file_read(step.get("file_path"))
        
    elif action_type == "file_list":
        # Note: assuming agent.file_list exists, or using run_terminal as fallback
        # Let's check if agent has file_list. If not, use run_terminal.
        # Based on previous view, agent has file_read, file_write, run_terminal.
        return await agent.run_terminal(f"ls -la {step.get('file_path')}")
        
    elif action_type == "terminal":
        from config import settings
        return await agent.run_terminal(step.get("command"), step.get("cwd", settings.user_home))
        
    elif action_type == "done":
        return {"success": True, "message": "Task complete"}
    
    return {"error": f"Unknown action_type: {action_type}"}

def is_meaningful_memory(content: str) -> bool:
    if not content or len(content) < 40:
        return False
    bad_prefixes = [
        "Step ", "Starting step", "Completed task:",
        "Executing:", "checkpoint", "Task complete",
        "step_result", "provider"
    ]
    if any(content.startswith(p) for p in bad_prefixes):
        return False
    return True

async def execute_task_loop(task_id: str):
    """The autonomous execution loop."""
    state = get_state(task_id)
    state["status"] = "running"
    
    project_name = state.get("project_name", "general")
    project_id = state.get("project_id", str(uuid.uuid4()))
    task_desc = state.get("task_description", "")

    cp_task = asyncio.create_task(checkpoint_loop(task_id))
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Init project memory
            await client.post(f"{settings.memory_url}/project/init", json={
                "project_id": project_id,
                "project_name": project_name
            })
            
            # 2. Search for relevant context
            mem_search = await client.post(f"{settings.memory_url}/memory/search", json={
                "query": task_desc,
                "project_name": project_name,
                "limit": 3
            })
            mem_results = mem_search.json().get("results", [])
            if mem_results:
                context_prefix = f"Previous work on this project: {mem_results[0].get('content')}\n\n"
                # This affects the context for planner calls if we were to re-plan, 
                # but for now we just log it.
                logger.info(f"Memory context found for task {task_id}")

        # 0. Try direct execution first to bypass LLM
        if await try_direct_execution(task_id):
            return

        plan = state["plan"]
        
        while state["current_step"] < len(plan):
            step = plan[state["current_step"]]
            await broadcast_event(task_id, "step_start", {"step": step})
            
            retry_count = 0
            success = False
            current_action = step
            
            while retry_count < 3 and not success:
                # ... [Existing retry and safety logic] ...
                if retry_count > 0:
                    await broadcast_event(task_id, "retrying", {"attempt": retry_count, "message": "Asking LLM for alternative approach..."})
                    current_action = await planner.get_alternative_approach(step, str(last_result.get("error", "Unknown error")), state["history"], task_id)
                    if not current_action: break

                if current_action.get("action_type") == "terminal":
                    cmd = current_action.get("command", "").lower()
                    if any(k in cmd for k in ["rm", "rmdir", "delete"]):
                        if not any(word in task_desc.lower() for word in ["delete", "remove", "clean"]):
                            await broadcast_event(task_id, "safety_skip", {"message": f"Skipped dangerous command: {cmd}"})
                            success = True; break

                await broadcast_event(task_id, "action", {"action": current_action})
                last_result = await execute_step(current_action)
                await broadcast_event(task_id, "result", {"result": last_result})

                # ... [Existing history and verification] ...
                state["history"].append({"step_index": state["current_step"], "attempt": retry_count, "action": current_action, "result": last_result})
                is_error = last_result.get("error") or (last_result.get("exit_code") is not None and last_result.get("exit_code") != 0)
                
                if not is_error:
                    success = True
                    # SAVE TO PROJECT MEMORY
                    try:
                        mem_content = f"Step {state['current_step'] + 1}: {step.get('description')} -> SUCCESS"
                        if is_meaningful_memory(mem_content):
                            async with httpx.AsyncClient() as client:
                                await client.post(f"{settings.memory_url}/memory/save", json={
                                    "project_name": project_name,
                                    "content": mem_content,
                                    "memory_type": "action"
                                })
                    except: pass
            
            state["current_step"] += 1
            await _save_checkpoint(task_id)
            
        # SAVE FINAL SUMMARY
        try:
            final_summary = f"Completed project: {project_name}. Task: {task_desc}. Result: success"
            if is_meaningful_memory(final_summary):
                async with httpx.AsyncClient() as client:
                    await client.post(f"{settings.memory_url}/memory/save", json={
                        "project_name": project_name,
                        "content": final_summary,
                        "memory_type": "task_summary"
                    })
        except: pass

        state["status"] = "completed"
        await broadcast_event(task_id, "completed", {"message": "Task complete"})
            
    except asyncio.CancelledError:
        state["status"] = "paused"
        await broadcast_event(task_id, "paused", {"message": "Task paused"})
    except Exception as e:
        logger.error(f"Fatal error in task loop: {e}")
        state["status"] = "error"
        await broadcast_event(task_id, "fatal_error", {"error": str(e)})
    finally:
        cp_task.cancel()
        if task_id in active_tasks:
            del active_tasks[task_id]

async def execute_autonomous_cursor(task_id: str, instruction: str, project_path: str, max_rounds: int = 10):
    """The autonomous loop for interacting with Cursor."""
    state = get_state(task_id)
    state["status"] = "running"
    state["task_description"] = instruction
    
    rounds_executed = 0
    commands_executed_total = []
    
    try:
        # Step 1: Focus Cursor and send initial instruction
        await broadcast_event(task_id, "cursor_autonomous", {"message": f"Starting autonomous loop. Instruction: {instruction}"})
        await broadcast_event(task_id, "cursor_autonomous", {"message": "Round 1: Focusing Cursor and sending instruction..."})
        
        # We use agent.py wrappers which call the local agent
        # Need to ensure agent has cursor_type and screenshot methods
        # For now, let's call the local agent directly via httpx in this loop for simplicity
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"Authorization": f"Bearer {settings.local_agent_secret}"}
            
            # Initial focus and type
            await client.post(f"{settings.agent_url}/cursor/type", json={"text": instruction}, headers=headers)
            
            while rounds_executed < max_rounds:
                rounds_executed += 1
                
                # Wait for Cursor to respond
                await broadcast_event(task_id, "cursor_autonomous", {"message": f"Round {rounds_executed}: Waiting 8s for Cursor to respond..."})
                await asyncio.sleep(8)
                
                # Take screenshot
                await broadcast_event(task_id, "cursor_autonomous", {"message": f"Round {rounds_executed}: Taking screenshot..."})
                resp = await client.post(f"{settings.agent_url}/browser/screenshot", headers=headers)
                screenshot_data = resp.json()
                image_b64 = screenshot_data.get("image_base64")
                
                if not image_b64:
                    await broadcast_event(task_id, "cursor_autonomous", {"message": "Error: Failed to capture screenshot."})
                    break
                
                # Extract commands via LLM
                await broadcast_event(task_id, "cursor_autonomous", {"message": f"Round {rounds_executed}: Analyzing screenshot..."})
                vision_result = await planner.extract_commands_from_screenshot(image_b64, task_id)
                
                logger.info(f"Vision result for task {task_id}: {vision_result}")
                
                commands = vision_result.get("commands", [])
                is_done = vision_result.get("done", False)
                response_text = vision_result.get("response_text", "")
                
                if not commands:
                    logger.warning(f"No commands extracted in round {rounds_executed}. Cursor said: {response_text}")

                await broadcast_event(task_id, "cursor_autonomous", {
                    "message": f"Round {rounds_executed}: Cursor response: {response_text}",
                    "commands": commands,
                    "raw_vision_result": vision_result
                })
                
                if not commands and is_done:
                    await broadcast_event(task_id, "cursor_autonomous", {"message": "Task marked as complete by vision model."})
                    break
                
                # Execute commands
                for cmd in commands:
                    await broadcast_event(task_id, "cursor_autonomous", {"message": f"Executing: {cmd}"})
                    cmd_res = await agent.run_terminal(cmd, cwd=project_path)
                    commands_executed_total.append(cmd)
                    
                    # If error, send back to Cursor
                    if cmd_res.get("exit_code") != 0 or cmd_res.get("error"):
                        error_msg = cmd_res.get("stderr") or cmd_res.get("error")
                        await broadcast_event(task_id, "cursor_autonomous", {"message": f"Command failed, sending error back to Cursor: {error_msg}"})
                        await client.post(f"{settings.agent_url}/cursor/type", json={"text": f"Command failed with error: {error_msg}"}, headers=headers)
                        # Wait a bit after sending error
                        await asyncio.sleep(5)
                
                if is_done:
                    break
                    
                # If not done, maybe send a "Continue" or just wait
                if rounds_executed < max_rounds:
                    await broadcast_event(task_id, "cursor_autonomous", {"message": f"Round {rounds_executed} complete. Proceeding to next round..."})

        state["status"] = "completed"
        await broadcast_event(task_id, "completed", {
            "message": "Autonomous Cursor loop finished.",
            "rounds": rounds_executed,
            "commands": commands_executed_total
        })
        
        return {
            "success": True,
            "rounds": rounds_executed,
            "commands_executed": commands_executed_total,
            "final_status": "completed"
        }

    except Exception as e:
        logger.error(f"Error in autonomous loop: {e}")
        state["status"] = "error"
        await broadcast_event(task_id, "fatal_error", {"error": str(e)})
        return {"success": False, "error": str(e)}

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
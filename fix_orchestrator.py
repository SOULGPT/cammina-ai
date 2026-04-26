import re

# Read the file
with open('services/orchestrator/main.py', 'r') as f:
    content = f.read()

# Remove any broken quick endpoint
content = re.sub(r'@\[?app\.post\]?\([^)]*task/quick[^)]*\).*', '', content, flags=re.DOTALL)
content = content.rstrip()

# Add clean endpoint
endpoint = """

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
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as e:
        return {"error": str(e)}
"""

content += endpoint

with open('services/orchestrator/main.py', 'w') as f:
    f.write(content)

print("Done! Endpoint added successfully.")

with open('services/orchestrator/main.py', 'r') as f:
    content = f.read()

# Fix corrupted markdown decorators
content = content.replace('@[app.post](http://app.post)', '@app.post')
content = content.replace('@[app.get](http://app.get)', '@app.get')
content = content.replace('@[app.delete](http://app.delete)', '@app.delete')
content = content.replace('[uvicorn.run](http://uvicorn.run)', 'uvicorn.run')
content = content.replace('[client.post](http://client.post)', 'client.post')
content = content.replace('[c.post](http://c.post)', 'c.post')

with open('services/orchestrator/main.py', 'w') as f:
    f.write(content)

print("Fixed all corrupted markdown links!")

# Verify
with open('services/orchestrator/main.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'task_quick' in line or ('app.post' in line and 'quick' in line):
        print(f"Line {i+1}: {line.rstrip()}")

import re

with open('services/orchestrator/main.py', 'rb') as f:
    content = f.read().decode('utf-8')

print("Before fix, occurrences of corrupted decorator:")
print(content.count('@[app.post]'))

# Fix all corrupted patterns using raw string replacement
replacements = [
    ('@[app.post](http://app.post)', '@app.post'),
    ('@[app.get](http://app.get)', '@app.get'),
    ('@[app.delete](http://app.delete)', '@app.delete'),
    ('@[app.put](http://app.put)', '@app.put'),
    ('@[app.patch](http://app.patch)', '@app.patch'),
    ('[uvicorn.run](http://uvicorn.run)', 'uvicorn.run'),
    ('[client.post](http://client.post)', 'client.post'),
    ('[c.post](http://c.post)', 'c.post'),
    ('[app.post](http://app.post)', 'app.post'),
]

for old, new in replacements:
    if old in content:
        print(f"Replacing: {old}")
        content = content.replace(old, new)

print("After fix, occurrences of corrupted decorator:")
print(content.count('@[app.post]'))

with open('services/orchestrator/main.py', 'wb') as f:
    f.write(content.encode('utf-8'))

print("\nDone! Lines with app.post:")
for i, line in enumerate(content.split('\n')):
    if 'app.post' in line:
        print(f"  Line {i+1}: {line.strip()}")

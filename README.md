# Cammina AI
### Your Autonomous AI Development Assistant

Cammina AI is a self-operating AI agent that runs on your Mac. 
Give it one command, it asks clarifying questions, then works 
completely autonomously until the task is done.

## Features
- Autonomous task execution
- Automatic LLM provider failover (OpenRouter, Nvidia, Groq)
- Persistent memory per project
- Real-time progress monitoring
- Local-first, completely free to run
- One command to start everything

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/SOULGPT/cammina-ai.git
cd cammina-ai
```

### 2. Install dependencies
```bash
pip3 install -r services/local_agent/requirements.txt
pip3 install -r services/llm_manager/requirements.txt
pip3 install -r services/memory/requirements.txt
pip3 install -r services/orchestrator/requirements.txt
cd apps/web && npm install && cd ../..
```

### 3. Set up environment
```bash
cp .env.example .env.local
# Edit .env.local and add your free API keys
```

### 4. Initialize database
```bash
python3 database/init_db.py
```

### 5. Start everything
```bash
./cammina start
```

### 6. Open browser
http://localhost:3000

## Free API Keys
- OpenRouter: https://openrouter.ai/keys
- Nvidia NIM: https://build.nvidia.com
- Groq: https://console.groq.com

## Architecture
- **Web UI**: React + TypeScript (port 3000)
- **Orchestrator**: FastAPI brain (port 8000)
- **LLM Manager**: Provider routing (port 8001)
- **Memory**: ChromaDB + SQLite (port 8002)
- **Local Agent**: Mac executor (port 8765)

## CLI Commands
```bash
./cammina start    # Start all services
./cammina stop     # Stop all services
./cammina status   # Check service status
./cammina restart  # Restart everything
./cammina logs     # View logs
```

## License
MIT License - Free to use and modify

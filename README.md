# Cammina AI 🤖
### Your Autonomous AI Development Assistant

Cammina AI is a self-operating AI agent that runs on your Mac.
Give it one command, it asks clarifying questions, then works
completely autonomously until the task is done.

## ✨ Features
- 🚀 **One command startup**: `./cammina start`
- 🤖 **Autonomous task execution** with LLM planning
- 🖥️ **Controls Cursor/Antigravity** automatically  
- 💾 **Project memory** - remembers everything per project
- 🔄 **Automatic LLM failover** (OpenRouter → Nvidia → Groq)
- 📁 **Full Control**: File operations, git commands, terminal control
- 🆓 **100% free to run** with free API tiers
- 🔓 **Fully open source**

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/SOULGPT/cammina-ai.git
cd cammina
```

### 2. Run install script
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

### 3. Add your free API keys
Edit `.env.local` and add at least one provider:
- **OpenRouter**: [https://openrouter.ai/keys](https://openrouter.ai/keys)
- **Nvidia NIM**: [https://build.nvidia.com](https://build.nvidia.com)
- **Groq**: [https://console.groq.com](https://console.groq.com)

### 4. Start Cammina AI
```bash
./cammina start
```

### 5. Open browser
[http://localhost:3000](http://localhost:3000)

## 💬 Quick Commands
Once running, type these directly in the chat to bypass the LLM planner:

| Command | Description |
|---------|-------------|
| `create a file at {path} with content: {code}` | Create any file instantly |
| `run app` | Auto-detects and starts your project |
| `cursor do: {instruction}` | Pilot Cursor autonomously |
| `git status` | Check git status of the project |
| `git push` | Push updates to GitHub |
| `show memory` | Show the last 10 project memories |
| `remember this: {note}` | Save an explicit project note |
| `clean memory` | Prune non-meaningful logs |
| `help` | Show all available commands |

## 🏗️ Architecture
- **Web UI**: React + TypeScript + Tailwind (port 3000)
- **Orchestrator**: The FastAPI "Brain" (port 8000)
- **LLM Manager**: Provider routing & failover (port 8001)
- **Memory**: ChromaDB + SQLite (port 8002)
- **Local Agent**: macOS executor & scraper (port 8765)

## 🛠️ CLI Commands
```bash
./cammina start    # Start all services
./cammina stop     # Stop all services
./cammina status   # Check service status
./cammina restart  # Restart everything
./cammina logs     # View live logs
```

## 📋 Requirements
- **macOS** (Apple Silicon or Intel)
- **Python 3.9+**
- **Node.js 18+**
- **npm**

## 📄 License
MIT License - Free to use, modify, and distribute.

---
Built with ❤️ for the open-source community by [SOULGPT](https://github.com/SOULGPT).

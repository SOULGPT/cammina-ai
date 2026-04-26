# Cammina-AI

> **Local-first AI orchestration platform** — a monorepo powering a React frontend and a suite of Python microservices for LLM routing, vector memory, and on-device tool execution.

---

## 📁 Project Structure

```
Cammina/
├── apps/
│   └── web/              # React 19 + TypeScript + Tailwind CSS + shadcn/ui
├── services/
│   ├── orchestrator/     # FastAPI gateway (port 8000)
│   ├── llm_manager/      # LLM routing (OpenAI · Anthropic · Ollama)
│   ├── memory/           # Vector memory service (Qdrant)
│   └── local_agent/      # File system & shell tool executor
├── database/
│   ├── schema.sql        # PostgreSQL + pgvector schema
│   └── migrations/       # Incremental SQL migrations
├── logs/                 # Shared log output
├── config/               # Shared configuration files
├── .env.local            # Environment variables (git-ignored)
├── docker-compose.yml    # Full stack orchestration
└── pnpm-workspace.yaml   # pnpm monorepo config
```

## 🚀 Quick Start

### Prerequisites
- **Node.js** ≥ 20
- **pnpm** ≥ 9  (`curl -fsSL https://get.pnpm.io/install.sh | sh -`)
- **Python** ≥ 3.11
- **Docker** + **Docker Compose** (for infrastructure)

### 1. Install Node dependencies

```bash
pnpm install
```

### 2. Start infrastructure (Postgres, Redis, Qdrant)

```bash
docker-compose up -d db redis qdrant
```

### 3. Start the web dev server

```bash
pnpm dev
# → http://localhost:3000
```

### 4. Start Python services

```bash
# Orchestrator
cd services/orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Repeat for llm_manager, memory, local_agent in separate terminals
```

### 5. Full stack with Docker

```bash
docker-compose --profile full up --build
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Gateway | FastAPI, Uvicorn, httpx |
| LLM Routing | OpenAI SDK, Anthropic SDK, Ollama |
| Memory | Qdrant (pgvector fallback) |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Monorepo | pnpm workspaces |
| Containers | Docker Compose |

---

## 🔑 Environment Variables

Copy `.env.local` and fill in your secrets. Key variables:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OLLAMA_BASE_URL` | Ollama server URL (default local) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret |

---

## 📜 License

MIT © Cammina-AI Contributors

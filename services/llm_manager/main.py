import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
import database
from router import LLMRouter

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

llm_router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_router
    database.init_db()
    llm_router = LLMRouter()
    logger.info("Cammina LLM Manager started.")
    yield
    await llm_router.close()
    logger.info("Cammina LLM Manager shutting down.")

app = FastAPI(
    title="Cammina LLM Manager",
    description="Handles all AI API calls with automatic failover.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class Message(BaseModel):
    role: str
    content: str

class CompleteRequest(BaseModel):
    messages: list[Message]
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    max_tokens: int = 1000

class CompleteResponse(BaseModel):
    response: str
    provider_used: str
    tokens_used: int

class TestRequest(BaseModel):
    provider: str

# --- Endpoints ---

@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "healthy",
        "service": "cammina-llm-manager"
    }

@app.post("/complete", response_model=CompleteResponse, tags=["llm"])
async def complete(req: CompleteRequest):
    messages_dicts = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        result = await llm_router.complete(messages_dicts, req.task_id, max_tokens=req.max_tokens)
        return CompleteResponse(**result)
    except Exception as e:
        logger.error(f"Completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers", tags=["system"])
async def get_providers():
    providers = database.get_active_providers()
    return {"providers": providers}

@app.post("/providers/test", tags=["system"])
async def test_provider(req: TestRequest):
    messages = [{"role": "user", "content": "Say 'hello' in exactly one word."}]
    try:
        # Temporarily force the router to use ONLY the requested provider
        original_providers = database.get_active_providers()
        found = any(p["provider_name"] == req.provider for p in original_providers)
        if not found:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

        # Dirty but quick hack: bypass the DB active list just to test the raw client
        import time
        t0 = time.perf_counter()
        
        # Test directly via the router's clients
        if req.provider in llm_router.clients:
            client = llm_router.clients[req.provider]
            res = await client.chat.completions.create(
                model=llm_router.models[req.provider],
                messages=messages,
                max_tokens=10
            )
        elif req.provider == "ollama":
            url = f"{settings.ollama_base_url}/api/chat"
            payload = {
                "model": llm_router.models["ollama"],
                "messages": messages,
                "stream": False
            }
            resp = await llm_router.httpx_client.post(url, json=payload)
            resp.raise_for_status()
        else:
            raise HTTPException(status_code=400, detail=f"Client not configured for {req.provider}")
            
        latency = int((time.perf_counter() - t0) * 1000)
        return {
            "success": True,
            "provider": req.provider,
            "latency_ms": latency
        }
    except Exception as e:
        return {
            "success": False,
            "provider": req.provider,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.llm_manager_host, port=settings.llm_manager_port, reload=True)

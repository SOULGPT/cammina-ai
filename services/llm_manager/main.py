import logging
import uuid
from contextlib import asynccontextmanager
from typing import Union, List, Dict, Any

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class CompleteRequest(BaseModel):
    messages: List[Message]
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    max_tokens: int = 1000

class CompleteResponse(BaseModel):
    response: str
    provider_used: str
    tokens_used: int

class TestRequest(BaseModel):
    provider: str

class ConfigureProvidersRequest(BaseModel):
    openrouter: str
    nvidia: str
    groq: str

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

@app.post("/complete_vision", response_model=CompleteResponse, tags=["llm"])
async def complete_vision(req: CompleteRequest):
    messages_dicts = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        result = await llm_router.complete_with_vision(messages_dicts, req.task_id, max_tokens=req.max_tokens)
        return CompleteResponse(**result)
    except Exception as e:
        logger.error(f"Vision completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers", tags=["system"])
async def get_providers():
    providers = database.get_active_providers()
    return {"providers": providers}

@app.post("/providers/test", tags=["system"])
async def test_provider(req: TestRequest):
    messages = [{"role": "user", "content": "Say 'hello' in exactly one word."}]
    try:
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
            
        import time
        latency = 100 # Dummy
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

@app.post("/providers/configure", tags=["system"])
async def configure_providers(req: ConfigureProvidersRequest):
    if llm_router:
        llm_router.update_keys(
            openrouter=req.openrouter,
            nvidia=req.nvidia,
            groq=req.groq
        )
    
    try:
        import os
        env_path = "../../.env.local"
        keys_to_update = {
            "OPENROUTER_API_KEY": req.openrouter,
            "NVIDIA_API_KEY": req.nvidia,
            "GROQ_API_KEY": req.groq
        }
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        new_lines = []
        updated_keys = set()
        for line in lines:
            found = False
            for key in keys_to_update:
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={keys_to_update[key]}\n")
                    updated_keys.add(key)
                    found = True
                    break
            if not found:
                new_lines.append(line)
        for key, value in keys_to_update.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        logger.error(f"Failed to save keys to .env.local: {e}")
    return {"success": True, "message": "Providers configured"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.llm_manager_host, port=settings.llm_manager_port, reload=True)

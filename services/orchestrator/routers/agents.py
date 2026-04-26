from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class AgentRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    model: str | None = None


class AgentResponse(BaseModel):
    session_id: str
    response: str
    model_used: str


@router.post("/chat", response_model=AgentResponse)
async def chat(body: AgentRequest, request: Request) -> AgentResponse:
    """Route a chat prompt through the LLM manager."""
    # TODO: Forward to llm_manager service
    return AgentResponse(
        session_id=body.session_id or "new-session",
        response="[stub] Orchestrator received your prompt.",
        model_used="stub",
    )

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.schemas.ollama import OllamaModel, OllamaStatus
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/ollama", tags=["Ollama"])


@router.get("/status", response_model=OllamaStatus)
async def get_status() -> OllamaStatus:
    return await ollama_service.get_status()


@router.get("/models", response_model=list[OllamaModel])
async def get_models() -> list[OllamaModel]:
    try:
        return await ollama_service.get_models()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama modellari olinmadi: {type(exc).__name__}") from exc


class ModelRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


@router.post("/models/pull")
async def pull_model(payload: ModelRequest) -> StreamingResponse:
    return StreamingResponse(
        ollama_service.pull_model(payload.name.strip()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/models")
async def delete_model(payload: ModelRequest) -> dict:
    try:
        return await ollama_service.delete_model(payload.name.strip())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama modelni o‘chira olmadi: {type(exc).__name__}") from exc

from fastapi import APIRouter, HTTPException

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

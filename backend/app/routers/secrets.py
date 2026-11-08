from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.secrets_service import secrets_service
from app.services.provider_runtime_service import provider_runtime_service

router = APIRouter(prefix="/api/secrets", tags=["Secrets"])


class SecretUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=8192)


@router.get("")
async def get_secret_status() -> dict[str, bool]:
    return secrets_service.status()


@router.put("")
async def save_secret(body: SecretUpdate) -> dict[str, bool]:
    try:
        secrets_service.set(body.name, body.value)
        runtime = provider_runtime_service.refresh_openai_adapter() if body.name == "openai-compatible-api-key" else None
        return {"saved": True, "provider_runtime": runtime}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Credential could not be saved.") from exc


@router.delete("/{name}")
async def delete_secret(name: str) -> dict[str, bool]:
    try:
        deleted = secrets_service.delete(name)
        runtime = provider_runtime_service.refresh_openai_adapter() if name == "openai-compatible-api-key" else None
        return {"deleted": deleted, "provider_runtime": runtime}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Credential could not be deleted.") from exc

from fastapi import APIRouter, HTTPException

from app.schemas.providers import (
    ActiveProviderSnapshot, ActiveProviderUpdate, ProviderCatalogSnapshot,
    ProviderPolicySnapshot, ProviderPolicyUpdate,
)
from app.services.provider_policy_service import provider_policy_service
from app.services.provider_runtime_service import provider_runtime_service

router = APIRouter(prefix="/api/providers", tags=["Providers"])


@router.get("/policy", response_model=ProviderPolicySnapshot)
async def get_policy() -> dict:
    return provider_policy_service.snapshot()


@router.put("/policy", response_model=ProviderPolicySnapshot)
async def update_policy(body: ProviderPolicyUpdate) -> dict:
    try:
        return provider_policy_service.update(body)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Provider policy could not be saved.") from exc


@router.get("/catalog", response_model=ProviderCatalogSnapshot)
async def get_provider_catalog() -> dict:
    try:
        return await provider_runtime_service.catalog()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Provider catalog could not be loaded.") from exc


@router.get("/active", response_model=ActiveProviderSnapshot)
async def get_active_provider() -> dict:
    return provider_runtime_service.active()


@router.put("/active", response_model=ActiveProviderSnapshot)
async def set_active_provider(body: ActiveProviderUpdate) -> dict:
    try:
        return provider_runtime_service.set_active(body.provider_id)
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

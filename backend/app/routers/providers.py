from fastapi import APIRouter, HTTPException

from app.schemas.providers import ProviderPolicySnapshot, ProviderPolicyUpdate
from app.services.provider_policy_service import provider_policy_service

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

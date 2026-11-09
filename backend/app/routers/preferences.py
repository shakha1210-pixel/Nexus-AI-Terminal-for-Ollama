from fastapi import APIRouter

from app.schemas.preferences import UIPreferences
from app.services.preferences_service import preferences_service

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


@router.get("", response_model=UIPreferences)
async def get_preferences() -> UIPreferences:
    return preferences_service.get()


@router.put("", response_model=UIPreferences)
async def update_preferences(body: UIPreferences) -> UIPreferences:
    return preferences_service.update(body)

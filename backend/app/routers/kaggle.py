from fastapi import APIRouter, HTTPException

from app.schemas.kaggle import KaggleStartRequest, KaggleStatus, ModeRequest
from app.services.kaggle_service import KaggleError, kaggle_service

router = APIRouter(prefix="/api/kaggle", tags=["Kaggle"])


@router.get("/status", response_model=KaggleStatus)
async def get_status() -> dict:
    return await kaggle_service.refresh()


@router.post("/start", response_model=KaggleStatus)
async def start(body: KaggleStartRequest) -> dict:
    try:
        await kaggle_service.start(body.model)
    except KaggleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return kaggle_service.snapshot()


@router.post("/mode", response_model=KaggleStatus)
async def set_mode(body: ModeRequest) -> dict:
    try:
        kaggle_service.set_mode(body.mode)
    except KaggleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return kaggle_service.snapshot()

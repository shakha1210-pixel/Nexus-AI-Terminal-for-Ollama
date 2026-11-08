from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.kaggle import router as kaggle_router
from app.routers.ollama import router as ollama_router
from app.routers.preferences import router as preferences_router

app = FastAPI(title=settings.app_name, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(ollama_router)
app.include_router(kaggle_router)
app.include_router(preferences_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}

from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.agents import router as agents_router
from app.routers.chat import router as chat_router
from app.routers.kaggle import router as kaggle_router
from app.routers.ollama import router as ollama_router
from app.routers.preferences import router as preferences_router
from app.routers.providers import router as providers_router
from app.routers.workspace import router as workspace_router


def resolve_frontend_dist() -> Path:
    configured = os.getenv("NEXUS_FRONTEND_DIST")
    if configured:
        return Path(configured).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "frontend" / "dist"


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.2.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(ollama_router)
    application.include_router(kaggle_router)
    application.include_router(preferences_router)
    application.include_router(providers_router)
    application.include_router(workspace_router)
    application.include_router(agents_router)
    application.include_router(chat_router)

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @application.api_route(
        "/api",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    @application.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def unknown_api_route(path: str = "") -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    static_dir = frontend_dist or resolve_frontend_dist()
    if static_dir.is_dir() and (static_dir / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True, check_dir=True),
            name="frontend",
        )

    return application


app = create_app()

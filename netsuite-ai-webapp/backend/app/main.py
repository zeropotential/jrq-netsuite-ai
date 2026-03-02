from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.admin.router import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.report import router as report_router
from app.api.routes.sql import router as sql_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import (
    AdminAuthMiddleware,
    MaxBodySizeMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)


def create_app() -> FastAPI:
    configure_logging()

    # Disable interactive API docs in production
    docs_url = "/docs" if settings.app_env == "dev" else None
    redoc_url = "/redoc" if settings.app_env == "dev" else None

    app = FastAPI(
        title="NetSuite AI Web App",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    # --- Middleware stack (applied bottom-to-top) ---
    # 1. Request ID
    app.add_middleware(RequestIdMiddleware)
    # 2. Security response headers
    app.add_middleware(SecurityHeadersMiddleware)
    # 3. API & Admin endpoint authentication
    app.add_middleware(AdminAuthMiddleware)
    # 4. Rate limiting
    app.add_middleware(RateLimitMiddleware)
    # 5. Max request body size
    app.add_middleware(MaxBodySizeMiddleware)

    # --- CORS ---
    origins: list[str] = []
    if settings.cors_origins:
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.app_env == "dev":
        # Allow localhost in dev
        origins += ["http://localhost", "http://localhost:8000", "http://127.0.0.1:8000"]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type", "Authorization", "X-OpenAI-Api-Key", "X-Request-ID"],
            max_age=600,
        )

    web_root = Path(__file__).resolve().parent / "web" / "index.html"

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_root)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(sql_router)
    app.include_router(report_router)
    app.include_router(admin_router)
    return app


app = create_app()

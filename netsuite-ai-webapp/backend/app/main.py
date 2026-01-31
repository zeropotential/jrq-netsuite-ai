from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.admin.router import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.report import router as report_router
from app.api.routes.sql import router as sql_router
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="NetSuite AI Web App", version="0.1.0")
    app.add_middleware(RequestIdMiddleware)

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

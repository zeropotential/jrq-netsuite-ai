from fastapi import APIRouter

from app.db.session import db_can_connect

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict:
    return {"status": "ok", "db": db_can_connect()}

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Ensure models are imported so Alembic sees them
from app.db import models as _models  # noqa: E402,F401

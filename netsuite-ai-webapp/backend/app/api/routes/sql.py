from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.sql_generator import LlmError, generate_oracle_sql

router = APIRouter(prefix="/api/sql", tags=["sql"])


class SqlTranslateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    schema_hint: str | None = None


class SqlTranslateResponse(BaseModel):
    sql: str
    model: str


@router.post("/translate", response_model=SqlTranslateResponse)
def translate(payload: SqlTranslateRequest) -> SqlTranslateResponse:
    try:
        result = generate_oracle_sql(prompt=payload.prompt, schema_hint=payload.schema_hint)
    except LlmError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SqlTranslateResponse(sql=result.sql, model=result.model)

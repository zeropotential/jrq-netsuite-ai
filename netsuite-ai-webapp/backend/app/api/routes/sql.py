from fastapi import APIRouter, Header, HTTPException
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
def translate(
    payload: SqlTranslateRequest,
    openai_api_key: str | None = Header(default=None, alias="X-OpenAI-Api-Key"),
) -> SqlTranslateResponse:
    try:
        result = generate_oracle_sql(
            prompt=payload.prompt,
            schema_hint=payload.schema_hint,
            api_key=openai_api_key,
        )
    except LlmError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SqlTranslateResponse(sql=result.sql, model=result.model)

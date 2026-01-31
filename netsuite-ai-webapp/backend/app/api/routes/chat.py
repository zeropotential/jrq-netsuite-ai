from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.llm.sql_generator import LlmError, generate_oracle_sql
from app.netsuite.jdbc import JdbcError, run_query

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    connection_id: str | None = None
    scope: str | None = None


class ChatResponse(BaseModel):
    answer: str
    source: str
    sql: str | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not payload.connection_id:
        raise HTTPException(status_code=400, detail="connection_id is required")

    prompt = payload.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message is required")

    sql = prompt
    normalized = sql.lower().lstrip()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        try:
            result = generate_oracle_sql(prompt=prompt, schema_hint=payload.scope)
        except LlmError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sql = result.sql
        normalized = sql.lower().lstrip()

    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise HTTPException(status_code=400, detail="LLM produced non-SELECT SQL")

    lowered = sql.lower()
    if " fetch first " not in lowered and " limit " not in lowered:
        sql = f"{sql.rstrip(';')} FETCH FIRST {settings.netsuite_jdbc_row_limit} ROWS ONLY"

    try:
        result = run_query(db, payload.connection_id, sql, settings.netsuite_jdbc_row_limit)
    except JdbcError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="JDBC query failed") from exc

    columns = result.get("columns", [])
    rows = result.get("rows", [])
    if not rows:
        answer = "Query executed successfully. No rows returned."
    else:
        header = " | ".join(columns) if columns else "(no columns)"
        lines = [header, "-" * max(len(header), 3)]
        for row in rows:
            lines.append(" | ".join(str(value) for value in row))
        answer = "\n".join(lines)

    return ChatResponse(answer=answer, source="netsuite_jdbc", sql=sql)

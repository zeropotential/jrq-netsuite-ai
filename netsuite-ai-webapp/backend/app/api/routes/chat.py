from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.llm.sql_generator import LlmError, generate_oracle_sql
from app.netsuite.jdbc import JdbcError, run_query

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    connection_id: str | None = None
    scope: str | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    source: str
    sql: str | None = None


def _get_openai_client(api_key: str | None) -> OpenAI:
    """Get OpenAI client with provided or configured API key."""
    key = api_key or settings.openai_api_key
    if not key:
        raise LlmError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=key)


def _classify_intent(client: OpenAI, message: str) -> str:
    """Classify user intent: 'data_query', 'general_question', or 'netsuite_help'."""
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify user messages into exactly one category. "
                    "Respond with ONLY one word:\n"
                    "- 'data_query' if the user wants to retrieve, count, list, or analyze data from NetSuite\n"
                    "- 'general_question' if asking about you, the AI, the model, or non-NetSuite topics\n"
                    "- 'netsuite_help' if asking for NetSuite advice, how-to, best practices, or explanations\n"
                    "Examples:\n"
                    "- 'how many employees' -> data_query\n"
                    "- 'list all customers' -> data_query\n"
                    "- 'what model are you using' -> general_question\n"
                    "- 'who are you' -> general_question\n"
                    "- 'do not run sql' -> general_question\n"
                    "- 'how do I create an invoice in NetSuite' -> netsuite_help\n"
                    "- 'what is revenue recognition' -> netsuite_help\n"
                    "- 'explain deferred revenue' -> netsuite_help"
                )
            },
            {"role": "user", "content": message}
        ],
        temperature=0,
        max_tokens=10,
    )
    intent = (response.choices[0].message.content or "").strip().lower()
    if intent not in ("data_query", "general_question", "netsuite_help"):
        # Default to data_query if unclear
        return "data_query"
    return intent


def _answer_general_question(client: OpenAI, message: str, history: list[ChatMessage] | None = None) -> str:
    """Answer general questions about the AI itself."""
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a NetSuite AI Assistant powered by OpenAI's {settings.openai_model} model. "
                "You help users with NetSuite questions, data queries, and functional consulting. "
                "When asked about yourself, be helpful and informative. "
                "You can query NetSuite data via JDBC when users ask for data. "
                "You remember the conversation history within this session."
            )
        }
    ]
    # Add conversation history
    if history:
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )
    return (response.choices[0].message.content or "").strip()


def _answer_netsuite_help(client: OpenAI, message: str, history: list[ChatMessage] | None = None) -> str:
    """Answer NetSuite functional/accounting questions like a consultant."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert NetSuite Functional Consultant and Certified Accountant. "
                "You have deep knowledge of:\n"
                "- NetSuite ERP modules: Financials, CRM, Inventory, Order Management, Projects\n"
                "- Accounting principles: GAAP, revenue recognition, deferred revenue, accruals\n"
                "- NetSuite best practices: workflows, saved searches, custom records, SuiteScript\n"
                "- Business processes: Order-to-Cash, Procure-to-Pay, Record-to-Report\n"
                "- Multi-subsidiary, multi-currency, and intercompany transactions\n\n"
                "Provide clear, practical advice. Use examples when helpful. "
                "If the user needs data, suggest they ask a data question. "
                "You remember the conversation history within this session."
            )
        }
    ]
    # Add conversation history
    if history:
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )
    return (response.choices[0].message.content or "").strip()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    openai_api_key: str | None = Header(default=None, alias="X-OpenAI-Api-Key"),
) -> ChatResponse:
    prompt = payload.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message is required")

    # Get OpenAI client
    try:
        client = _get_openai_client(openai_api_key)
    except LlmError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Check if user provided raw SQL
    normalized = prompt.lower().lstrip()
    is_raw_sql = normalized.startswith("select") or normalized.startswith("with")

    # If not raw SQL, classify the intent
    if not is_raw_sql:
        intent = _classify_intent(client, prompt)
        
        # Handle general questions (about the AI, model, etc.)
        if intent == "general_question":
            answer = _answer_general_question(client, prompt, payload.history)
            return ChatResponse(answer=answer, source="assistant", sql=None)
        
        # Handle NetSuite help/consulting questions
        if intent == "netsuite_help":
            answer = _answer_netsuite_help(client, prompt, payload.history)
            return ChatResponse(answer=answer, source="consultant", sql=None)

    # For data queries, require connection_id
    if not payload.connection_id:
        raise HTTPException(
            status_code=400, 
            detail="To query NetSuite data, please select a JDBC connection first."
        )

    # Generate SQL if not raw SQL
    sql = prompt
    if not is_raw_sql:
        try:
            result = generate_oracle_sql(prompt=prompt, schema_hint=payload.scope, api_key=openai_api_key)
        except LlmError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sql = result.sql
        normalized = sql.lower().lstrip()

    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise HTTPException(status_code=400, detail="LLM produced non-SELECT SQL")

    # Always strip trailing semicolon (not valid for NetSuite JDBC)
    sql = sql.rstrip(';').strip()

    lowered = sql.lower()
    # Only add ROWNUM limit if no limit clause and not an aggregate-only query
    has_limit = "rownum" in lowered or " limit " in lowered or " fetch first " in lowered
    is_aggregate_only = (
        ("count(" in lowered or "sum(" in lowered or "avg(" in lowered or "max(" in lowered or "min(" in lowered)
        and "group by" not in lowered
    )
    if not has_limit and not is_aggregate_only:
        # Wrap query with ROWNUM for SQL-92 compatibility
        sql = f"SELECT * FROM ({sql}) WHERE ROWNUM <= {settings.netsuite_jdbc_row_limit}"

    try:
        result = run_query(db, payload.connection_id, sql, settings.netsuite_jdbc_row_limit)
    except JdbcError as exc:
        raise HTTPException(status_code=400, detail=f"{exc} | SQL: {sql}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"JDBC query failed | SQL: {sql}") from exc

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

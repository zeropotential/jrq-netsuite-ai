import logging
import traceback

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.llm.sql_generator import LlmError, generate_oracle_sql, _get_completion_kwargs
from app.netsuite.jdbc import JdbcError, run_query

logger = logging.getLogger(__name__)

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
                    "You are an intent classifier. Your job is to determine what type of request the user is making.\n\n"
                    "RESPOND WITH EXACTLY ONE OF THESE THREE WORDS (nothing else):\n"
                    "- data_query\n"
                    "- general_question\n"
                    "- netsuite_help\n\n"
                    "CLASSIFICATION RULES:\n"
                    "1. 'data_query' - User wants to GET DATA from a database (count, list, show, get, find, retrieve, "
                    "total, sum, how many records/rows, sales figures, employee list, customer data, etc.)\n"
                    "2. 'general_question' - User is asking about YOU (the AI), your capabilities, who you are, what model "
                    "you use, greetings like 'hello', 'hi', or ANY non-NetSuite topic\n"
                    "3. 'netsuite_help' - User wants ADVICE or EXPLANATIONS about NetSuite processes, features, "
                    "workflows, best practices (NOT data retrieval)\n\n"
                    "EXAMPLES:\n"
                    "- 'how many employees' -> data_query (wants count from database)\n"
                    "- 'list all customers' -> data_query (wants data from database)\n"
                    "- 'what is your name' -> general_question (asking about AI)\n"
                    "- 'who are you' -> general_question (asking about AI)\n"
                    "- 'hello' -> general_question (greeting)\n"
                    "- 'what can you do' -> general_question (asking about AI capabilities)\n"
                    "- 'how do I create an invoice' -> netsuite_help (wants process advice)\n"
                    "- 'what is revenue recognition' -> netsuite_help (wants explanation)\n\n"
                    "IMPORTANT: Only output ONE word. No explanations."
                )
            },
            {"role": "user", "content": f"Classify this message: {message}"}
        ],
        **_get_completion_kwargs(20, temperature=0),
    )
    raw_intent = (response.choices[0].message.content or "").strip().lower()
    logger.info(f"Raw intent response: '{raw_intent}'")
    
    # Extract the intent keyword from the response
    if "data_query" in raw_intent:
        intent = "data_query"
    elif "general_question" in raw_intent:
        intent = "general_question"
    elif "netsuite_help" in raw_intent:
        intent = "netsuite_help"
    else:
        # Default to general_question if unclear (safer than running SQL)
        logger.warning(f"Could not parse intent from '{raw_intent}', defaulting to general_question")
        intent = "general_question"
    
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
        **_get_completion_kwargs(500, temperature=0.7),
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
        **_get_completion_kwargs(1000, temperature=0.7),
    )
    return (response.choices[0].message.content or "").strip()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    openai_api_key: str | None = Header(default=None, alias="X-OpenAI-Api-Key"),
) -> ChatResponse:
    logger.info(f"Chat request received: {payload.message[:100]}...")
    
    prompt = payload.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message is required")

    # Get OpenAI client
    try:
        client = _get_openai_client(openai_api_key)
    except LlmError as exc:
        logger.error(f"OpenAI client error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Check if user provided raw SQL
    normalized = prompt.lower().lstrip()
    is_raw_sql = normalized.startswith("select") or normalized.startswith("with")

    # If not raw SQL, classify the intent
    if not is_raw_sql:
        try:
            logger.info(f"Classifying intent for: {prompt[:50]}...")
            intent = _classify_intent(client, prompt)
            logger.info(f"Intent classified as: {intent}")
        except AuthenticationError as exc:
            logger.error(f"OpenAI authentication error: {exc}")
            raise HTTPException(status_code=401, detail=f"OpenAI API authentication failed: {exc.message}") from exc
        except RateLimitError as exc:
            logger.error(f"OpenAI rate limit error: {exc}")
            raise HTTPException(status_code=429, detail=f"OpenAI API rate limit exceeded: {exc.message}") from exc
        except APIConnectionError as exc:
            logger.error(f"OpenAI connection error: {exc}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to OpenAI API: {exc}") from exc
        except APIError as exc:
            logger.error(f"OpenAI API error: {exc}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {exc.message}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error during intent classification: {exc}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error classifying intent: {type(exc).__name__}: {exc}") from exc
        
        # Handle general questions (about the AI, model, etc.)
        if intent == "general_question":
            try:
                answer = _answer_general_question(client, prompt, payload.history)
                return ChatResponse(answer=answer, source="assistant", sql=None)
            except Exception as exc:
                logger.error(f"Error in general question: {exc}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Error generating response: {type(exc).__name__}: {exc}") from exc
        
        # Handle NetSuite help/consulting questions
        if intent == "netsuite_help":
            try:
                answer = _answer_netsuite_help(client, prompt, payload.history)
                return ChatResponse(answer=answer, source="consultant", sql=None)
            except Exception as exc:
                logger.error(f"Error in netsuite help: {exc}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Error generating response: {type(exc).__name__}: {exc}") from exc

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
            logger.info(f"Generating SQL for: {prompt[:50]}...")
            result = generate_oracle_sql(prompt=prompt, schema_hint=payload.scope, api_key=openai_api_key)
            sql = result.sql
            logger.info(f"Generated SQL: {sql[:100]}...")
        except LlmError as exc:
            logger.error(f"LLM error: {exc}")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.error(f"Error generating SQL: {exc}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error generating SQL: {type(exc).__name__}: {exc}") from exc
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
        logger.info(f"Executing SQL: {sql[:100]}...")
        result = run_query(db, payload.connection_id, sql, settings.netsuite_jdbc_row_limit)
    except JdbcError as exc:
        logger.error(f"JDBC error: {exc}")
        raise HTTPException(status_code=400, detail=f"{exc} | SQL: {sql}") from exc
    except Exception as exc:
        logger.error(f"Query execution error: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"JDBC query failed: {type(exc).__name__}: {exc} | SQL: {sql}") from exc

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

    logger.info(f"Chat response: {len(rows)} rows returned")
    return ChatResponse(answer=answer, source="netsuite_jdbc", sql=sql)

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


class KnowledgeBaseEntry(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    connection_id: str | None = None
    scope: str | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    kb_entries: list[KnowledgeBaseEntry] = Field(default_factory=list, max_length=20)


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
    """Use LLM to classify user intent: 'data_query', 'general_question', or 'netsuite_help'."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an intent classifier for a NetSuite AI Assistant. "
                        "Analyze the user's message and determine which persona should handle it.\n\n"
                        "RESPOND WITH EXACTLY ONE OF THESE THREE OPTIONS:\n\n"
                        "1. data_query - User wants to retrieve, query, count, list, or analyze DATA from NetSuite database. "
                        "Examples: 'how many employees', 'list customers', 'show me sales', 'count invoices', 'get transactions'\n\n"
                        "2. general_question - User is making conversation, asking about the AI itself, greetings, "
                        "or topics unrelated to NetSuite. "
                        "Examples: 'hi', 'hello', 'who are you', 'what model are you', 'thanks', 'what can you do'\n\n"
                        "3. netsuite_help - User wants advice, explanations, best practices, or help about NetSuite "
                        "processes and features (NOT data retrieval). "
                        "Examples: 'how do I create an invoice', 'explain revenue recognition', 'what is deferred revenue'\n\n"
                        "Reply with ONLY the category name, nothing else."
                    )
                },
                {"role": "user", "content": message}
            ],
        )
        raw_intent = (response.choices[0].message.content or "").strip().lower()
        logger.info(f"LLM intent classification: '{raw_intent}'")
        
        # Extract the intent keyword from the response
        if "data_query" in raw_intent or "data" in raw_intent:
            return "data_query"
        elif "general_question" in raw_intent or "general" in raw_intent:
            return "general_question"
        elif "netsuite_help" in raw_intent or "help" in raw_intent:
            return "netsuite_help"
        else:
            logger.warning(f"Could not parse LLM intent from '{raw_intent}', defaulting to general_question")
            return "general_question"
    except Exception as e:
        logger.error(f"LLM classification failed: {e}, defaulting to general_question")
        return "general_question"


def _format_kb_context(kb_entries: list[KnowledgeBaseEntry] | None) -> str:
    if not kb_entries:
        return ""
    lines = ["KNOWLEDGE BASE (use as authoritative context):"]
    for entry in kb_entries:
        lines.append(f"- {entry.title}: {entry.content}")
    return "\n".join(lines)


def _answer_general_question(
    client: OpenAI,
    message: str,
    history: list[ChatMessage] | None = None,
    kb_entries: list[KnowledgeBaseEntry] | None = None,
) -> str:
    """Answer general questions about the AI itself."""
    kb_context = _format_kb_context(kb_entries)
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
    if kb_context:
        messages.append({"role": "system", "content": kb_context})
    # Add conversation history
    if history:
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        **_get_completion_kwargs(4096, temperature=0.7),
    )
    return (response.choices[0].message.content or "").strip()


def _answer_netsuite_help(
    client: OpenAI,
    message: str,
    history: list[ChatMessage] | None = None,
    kb_entries: list[KnowledgeBaseEntry] | None = None,
) -> str:
    """Answer NetSuite functional/accounting questions like a consultant."""
    kb_context = _format_kb_context(kb_entries)
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
    if kb_context:
        messages.append({"role": "system", "content": kb_context})
    # Add conversation history
    if history:
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        **_get_completion_kwargs(4096, temperature=0.7),
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
                answer = _answer_general_question(client, prompt, payload.history, payload.kb_entries)
                return ChatResponse(answer=answer, source="assistant", sql=None)
            except Exception as exc:
                logger.error(f"Error in general question: {exc}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Error generating response: {type(exc).__name__}: {exc}") from exc
        
        # Handle NetSuite help/consulting questions
        if intent == "netsuite_help":
            try:
                answer = _answer_netsuite_help(client, prompt, payload.history, payload.kb_entries)
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
            result = generate_oracle_sql(
                prompt=prompt,
                schema_hint=payload.scope,
                api_key=openai_api_key,
                kb_context=_format_kb_context(payload.kb_entries),
            )
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

    # Do not auto-wrap or limit SQL here. SuiteAnalytics requires TOP in the same
    # SELECT as ORDER BY, and wrapping can invalidate queries.

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

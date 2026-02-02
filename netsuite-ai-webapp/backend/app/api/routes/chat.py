import json
import logging
import traceback

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.llm.sql_generator import LlmError, generate_oracle_sql, generate_postgres_sql, _get_completion_kwargs
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
    query_mode: str = Field(default="postgres", pattern="^(netsuite|postgres)$", description="Query mode: 'postgres' for local mirror (default, faster), 'netsuite' for direct JDBC")


class ChatResponse(BaseModel):
    answer: str
    source: str
    sql: str | None = None
    html: str | None = None


# Fast model for quick tasks like intent classification (reasoning models are too slow)
FAST_MODEL = "gpt-5-mini"


def _get_openai_client(api_key: str | None) -> OpenAI:
    """Get OpenAI client with provided or configured API key."""
    key = api_key or settings.openai_api_key
    if not key:
        raise LlmError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=key, timeout=120.0)  # 2 minute timeout


def _classify_intent(client: OpenAI, message: str) -> str:
    """Use LLM to classify user intent: 'data_query', 'general_question', 'netsuite_help', or 'unsupported_data'."""
    try:
        # Use fast model for classification - reasoning models (o1/o3) are too slow for this
        response = client.chat.completions.create(
            model=FAST_MODEL,
            timeout=30.0,  # 30 second timeout for classification
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an intent classifier for a NetSuite AI Assistant. "
                        "Analyze the user's message and determine which persona should handle it.\n\n"
                        "RESPOND WITH EXACTLY ONE OF THESE FOUR OPTIONS:\n\n"
                        "1. data_query - User wants to retrieve, query, count, list, or analyze DATA from available tables. "
                        "Available tables: account, employee, customer, transaction, transactionline. "
                        "Examples: 'how many employees', 'list customers', 'show me invoices', 'count transactions', 'customer balance'\n\n"
                        "2. unsupported_data - User wants data that is NOT in available tables. "
                        "NOT available: items, vendors, inventory, purchase orders, departments, classes, subsidiaries, locations, etc. "
                        "Examples: 'list all items', 'show inventory', 'how many vendors', 'get purchase orders', 'show departments'\n\n"
                        "3. general_question - User is making conversation, asking about the AI itself, greetings, "
                        "or topics unrelated to NetSuite. "
                        "Examples: 'hi', 'hello', 'who are you', 'what model are you', 'thanks', 'what can you do'\n\n"
                        "4. netsuite_help - User wants advice, explanations, best practices, or help about NetSuite "
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
        if "unsupported_data" in raw_intent or "unsupported" in raw_intent:
            return "unsupported_data"
        elif "data_query" in raw_intent or "data" in raw_intent:
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


def _generate_html_visualization(
    client: OpenAI,
    user_request: str,
    columns: list[str],
    rows: list[list],
    sql: str,
) -> str:
    """Generate HTML visualization (charts, tables, graphs) from query results using LLM."""
    # Limit data for context window - keep it small to avoid timeouts
    sample_rows = rows[:50]  # Max 50 rows for visualization
    
    # Format data as JSON for the LLM
    data_json = json.dumps({"columns": columns, "rows": sample_rows}, default=str)
    
    messages = [
        {
            "role": "system",
            "content": '''You are a data visualization expert. Generate a complete, self-contained HTML snippet that visualizes the provided data.

RULES:
1. Use Chart.js (CDN: https://cdn.jsdelivr.net/npm/chart.js) for charts/graphs
2. Create clean, professional visualizations with good colors
3. Choose the BEST visualization type based on the data and user request:
   - Bar charts for comparisons
   - Line charts for trends over time
   - Pie/Doughnut charts for proportions
   - Tables for detailed data listings
   - Combine multiple visualizations if appropriate
4. Always include a styled HTML table showing the data
5. Use modern CSS styling (flexbox, clean fonts, subtle shadows)
6. Make it responsive and visually appealing
7. Include a title based on the user's question
8. Return ONLY the HTML code, no markdown, no code fences, no explanation
9. The HTML must be self-contained (inline styles and scripts)
10. Use a light color scheme that matches a professional dashboard

Color palette to use:
- Primary: #0f766e (teal)
- Secondary: #22c1a2 (light teal)  
- Accent colors: #3b82f6 (blue), #8b5cf6 (purple), #f59e0b (amber), #ef4444 (red), #22c55e (green)
- Background: #f8fafc
- Text: #0f172a
- Muted: #64748b'''
        },
        {
            "role": "user",
            "content": f"""User's question: {user_request}

SQL executed: {sql}

Data (JSON format):
{data_json}

Generate an HTML visualization dashboard for this data."""
        }
    ]
    
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        timeout=60.0,  # 60 second timeout for visualization
        **_get_completion_kwargs(4096, temperature=0.3),  # Reduced token limit
    )
    
    html = (response.choices[0].message.content or "").strip()
    
    # Clean up any markdown code fences if present
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    
    return html.strip()


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
        timeout=90.0,  # 90 second timeout
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
        timeout=90.0,  # 90 second timeout
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
        
        # Handle unsupported data requests
        if intent == "unsupported_data":
            answer = (
                "I can only query data from these synced tables:\n\n"
                "- **account** - Chart of accounts\n"
                "- **employee** - Employee records\n"
                "- **customer** - Customer records\n"
                "- **transaction** - Transaction headers (invoices, sales orders, payments, etc.)\n"
                "- **transactionline** - Transaction line details (amounts, items, quantities)\n\n"
                "The data you're asking about (items, vendors, inventory, purchase orders, departments, classes, etc.) "
                "is not currently synced to our database.\n\n"
                "Would you like to ask about accounts, employees, customers, or transactions instead?"
            )
            return ChatResponse(answer=answer, source="assistant", sql=None)
        
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

    # For data queries, require connection_id (unless using postgres mode)
    if not payload.connection_id and payload.query_mode == "netsuite":
        raise HTTPException(
            status_code=400, 
            detail="To query NetSuite data, please select a JDBC connection first."
        )

    # Determine if we're using PostgreSQL mode
    use_postgres = payload.query_mode == "postgres"
    query_source = "postgres_mirror" if use_postgres else "netsuite_jdbc"

    # Generate SQL if not raw SQL
    sql = prompt
    if not is_raw_sql:
        try:
            logger.info(f"Generating SQL for: {prompt[:50]}... (mode: {payload.query_mode})")
            
            if use_postgres:
                # Use PostgreSQL-specific SQL generator
                from app.netsuite.postgres_query import get_postgres_schema
                result = generate_postgres_sql(
                    prompt=prompt,
                    schema=get_postgres_schema(),
                    api_key=openai_api_key,
                    kb_context=_format_kb_context(payload.kb_entries),
                )
            else:
                result = generate_oracle_sql(
                    prompt=prompt,
                    schema_hint=payload.scope,
                    api_key=openai_api_key,
                    kb_context=_format_kb_context(payload.kb_entries),
                    db=db,
                    connection_id=payload.connection_id,
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
        logger.info(f"Executing SQL ({payload.query_mode} mode): {sql[:100]}...")
        
        if use_postgres:
            # Execute against PostgreSQL mirror tables
            from app.netsuite.postgres_query import execute_postgres_query
            result = execute_postgres_query(db, sql, limit=settings.netsuite_jdbc_row_limit)
            query_source = "postgres_mirror"
        else:
            # Execute against NetSuite JDBC
            result = run_query(db, payload.connection_id, sql, settings.netsuite_jdbc_row_limit)
            query_source = "netsuite_jdbc"
            
    except JdbcError as exc:
        logger.error(f"JDBC error: {exc}")
        raise HTTPException(status_code=400, detail=f"{exc} | SQL: {sql}") from exc
    except ValueError as exc:
        logger.error(f"Query error: {exc}")
        raise HTTPException(status_code=400, detail=f"{exc} | SQL: {sql}") from exc
    except Exception as exc:
        logger.error(f"Query execution error: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Query failed: {type(exc).__name__}: {exc} | SQL: {sql}") from exc

    columns = result.get("columns", [])
    rows = result.get("rows", [])
    if not rows:
        answer = "Query executed successfully. No rows returned."
        return ChatResponse(answer=answer, source=query_source, sql=sql, html=None)
    
    # Generate text summary
    header = " | ".join(columns) if columns else "(no columns)"
    lines = [header, "-" * max(len(header), 3)]
    for row in rows:
        lines.append(" | ".join(str(value) for value in row))
    answer = "\n".join(lines)
    
    # Generate HTML visualization
    html_content = None
    try:
        logger.info("Generating HTML visualization...")
        html_content = _generate_html_visualization(
            client=client,
            user_request=prompt,
            columns=columns,
            rows=rows,
            sql=sql,
        )
        logger.info(f"HTML visualization generated: {len(html_content)} chars")
    except Exception as exc:
        logger.warning(f"Failed to generate HTML visualization: {exc}")
        # Continue without visualization - not a fatal error

    logger.info(f"Chat response: {len(rows)} rows returned ({query_source})")
    return ChatResponse(answer=answer, source=query_source, sql=sql, html=html_content)

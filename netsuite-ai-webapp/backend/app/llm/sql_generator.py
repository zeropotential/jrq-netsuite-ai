from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from openai import OpenAI

from app.core.config import settings
from app.llm.netsuite_schema import NETSUITE_SCHEMA

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


@lru_cache
def _load_allowed_schema() -> str | None:
    csv_path = Path(__file__).resolve().parents[2] / "Table - FIeld List - Sheet1.csv"
    if not csv_path.exists():
        logger.warning("Allowed schema CSV not found: %s", csv_path)
        return None

    table_map: dict[str, set[str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            table = (row.get("Table Name in NetSuite2.com") or "").strip()
            field = (row.get("Field ID in NetSuite2.com") or "").strip()
            if not table or not field:
                continue
            if table in {"-", "N/A"} or field in {"-", "N/A"}:
                continue
            table_map.setdefault(table, set()).add(field)

    # Build compact schema representation
    lines = ["ALLOWED TABLES AND COLUMNS:"]
    for table in sorted(table_map):
        cols = ", ".join(sorted(table_map[table]))
        lines.append(f"- {table}: {cols}")
    
    schema_text = "\n".join(lines)
    logger.info(f"Loaded allowed schema: {len(table_map)} tables, {len(schema_text)} chars")
    
    return schema_text


@lru_cache
def _load_markdown_schema() -> str | None:
    md_path = Path(__file__).resolve().parent / "schema.md"
    if not md_path.exists():
        return None
    try:
        content = md_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning("Failed to read markdown schema: %s", exc)
        return None
    if not content:
        return None
    return f"MARKDOWN SCHEMA REFERENCE:\n{content}"


def _load_live_schema(db: "Session", connection_id: str) -> str | None:
    """
    Load live schema from cache if available.
    
    NOTE: Live schema discovery is OPTIONAL and slow.
    The markdown schema (schema.md) is the primary reference and is preferred.
    Live schema is only used if manually cached via admin endpoint.
    """
    try:
        from app.netsuite.schema_discovery import (
            get_cached_schema,
            schema_to_llm_context
        )
        
        # Only use cached schema - never block on discovery
        cached = get_cached_schema(connection_id)
        if cached:
            logger.debug("Using cached live schema for connection %s", connection_id)
            return schema_to_llm_context(cached)
        
        return None
    except Exception:
        # Silently fail - markdown schema is the primary source
        return None


@dataclass(frozen=True)
class SqlGenerationResult:
    sql: str
    model: str


def _require_openai_client(api_key: str | None) -> OpenAI:
    key = api_key or settings.openai_api_key
    if not key:
        raise LlmError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=key)


def _is_gpt5_model() -> bool:
    """Check if the configured model is a GPT-5 series model."""
    model = settings.openai_model.lower()
    return "gpt-5" in model or "o1" in model or "o3" in model


def _get_completion_kwargs(max_tokens: int, temperature: float | None = None) -> dict:
    """Return the appropriate parameters based on model.
    
    GPT-5 series:
    - Uses max_completion_tokens instead of max_tokens
    - Only supports temperature=1 (default), so we omit it
    """
    kwargs = {}
    
    if _is_gpt5_model():
        kwargs["max_completion_tokens"] = max_tokens
        # GPT-5 doesn't support custom temperature, omit it (defaults to 1)
    else:
        kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
    
    return kwargs


def generate_oracle_sql(
    *,
    prompt: str,
    schema_hint: str | None = None,
    max_tokens: int = 2048,
    api_key: str | None = None,
    kb_context: str | None = None,
    db: "Session | None" = None,
    connection_id: str | None = None,
) -> SqlGenerationResult:
    """
    Generate SuiteAnalytics Connect SQL from a natural language prompt.
    
    Args:
        prompt: Natural language description of the query
        schema_hint: Optional additional schema context
        max_tokens: Maximum tokens for LLM response
        api_key: Optional OpenAI API key override
        kb_context: Optional knowledge base context
        db: Optional database session for live schema discovery
        connection_id: Optional JDBC connection ID for live schema discovery
    
    Returns:
        SqlGenerationResult with generated SQL and model used
    """
    if settings.llm_provider.lower() != "openai":
        raise LlmError("Unsupported LLM provider")

    client = _require_openai_client(api_key)
    
    # Try to load live schema from database if connection provided
    live_schema: str | None = None
    if db is not None and connection_id:
        live_schema = _load_live_schema(db, connection_id)
        if live_schema:
            logger.info("Using live schema from OA_TABLES/OA_COLUMNS")

    # Build system messages for SuiteAnalytics Connect SQL expert
    system_messages = [
        {
            "type": "text",
            "text": "You are an expert in NetSuite SuiteAnalytics Connect (JDBC) SQL. All SQL you generate must be valid for the NetSuite OpenAccess SQL engine and executable without modification."
        },
        {
            "type": "text",
            "text": "SCHEMA RESTRICTION: You MUST ONLY use tables and columns listed in the schema references provided below. Use the LIVE DATABASE SCHEMA as the primary reference if available, supplemented by the MARKDOWN SCHEMA REFERENCE. Use exact table/column names (case-sensitive)."
        },
        {
            "type": "text",
            "text": (
                "KEY TABLES FROM SCHEMA:\n"
                "- transaction: Main transaction header table (PK: id). Contains dates, entity, status, memo, etc.\n"
                "- transactionLine: Line-level details. Contains amounts, quantities, accounts, items.\n"
                "- Always JOIN these tables on: T.id = TL.transaction"
            )
        },
        {
            "type": "text",
            "text": (
                "CORE DIALECT RULES (MANDATORY):\n"
                "1. Use SuiteAnalytics Connect SQL only. Do not use Oracle, Postgres, or MySQL syntax.\n"
                "2. Use TOP n to limit results. Never use ROWNUM, LIMIT, or OFFSET.\n"
                "3. ORDER BY is allowed only in the outermost query. ORDER BY inside subqueries or derived tables is invalid unless TOP is also specified in that same SELECT.\n"
                "4. Prefer a single-level SELECT with TOP + ORDER BY for top-N queries. Avoid wrapping queries just to apply limits.\n"
                "5. Use explicit JOIN syntax only. Never use implicit joins."
            )
        },
        {
            "type": "text",
            "text": (
                "TRANSACTION QUERY PATTERN (MANDATORY):\n"
                "When querying transaction data, ALWAYS join transaction with transactionLine:\n"
                "```\n"
                "SELECT T.id, T.tranid, T.trandate, T.type, T.status,\n"
                "       TL.id AS line_id, TL.item, TL.amount, TL.netamount\n"
                "FROM transaction T\n"
                "INNER JOIN transactionLine TL ON T.id = TL.transaction\n"
                "WHERE T.posting = 'T'\n"
                "```\n"
                "- transaction table has header info: dates, entity, status, memo, type\n"
                "- transactionLine table has line details: amounts, quantities, items, accounts\n"
                "- NEVER query transaction alone when amounts, items, or quantities are needed\n"
                "- Use LEFT JOIN only if you need transactions even without lines"
            )
        },
        {
            "type": "text",
            "text": (
                "TRANSACTION AND LINE RULES:\n"
                "1. The main transaction table is 'transaction' (primary key: id).\n"
                "2. The line-level detail table is 'transactionLine'.\n"
                "3. JOIN transaction T to transactionLine TL using: T.id = TL.transaction.\n"
                "4. Credit/debit amounts and quantities are in transactionLine, NOT in transaction.\n"
                "5. Use valid SuiteAnalytics Connect JDBC column names only (e.g., TL.amount, TL.netamount).\n"
                "6. When filtering posting transactions, use T.posting = 'T' (VARCHAR2 'T'/'F').\n"
                "7. Transaction type is T.type (e.g., 'CustInvc', 'SalesOrd', 'VendBill')."
            )
        },
        {
            "type": "text",
            "text": (
                "DATES, NULLS, AND AGGREGATION:\n"
                "1. Use TO_DATE('YYYY-MM-DD','YYYY-MM-DD') for date comparisons.\n"
                "2. Use COALESCE() for null handling.\n"
                "3. Every non-aggregated column in SELECT must appear in GROUP BY.\n"
                "4. For revenue/amounts, prefer TL.amount or TL.net_amount from Transaction_lines.\n"
                "5. Always use table aliases and fully qualify column references.\n"
                "6. Transaction date is T.trandate; created date is T.create_date."
            )
        },
        {
            "type": "text",
            "text": (
                "FORBIDDEN PATTERNS:\n"
                "- ROWNUM, LIMIT, OFFSET\n"
                "- ORDER BY inside subqueries without TOP\n"
                "- Implicit joins\n"
                "- Invalid or non-existent JDBC columns\n"
                "- Wrapping a query solely to apply ORDER BY or limits\n"
                "- Using columns that don't exist in the schema (always verify against MARKDOWN SCHEMA REFERENCE)"
            )
        },
        {
            "type": "text",
            "text": (
                "SELF-CRITIQUE STEP (REQUIRED BEFORE FINAL OUTPUT):\n"
                "Before producing the final SQL, silently validate the query against the following checklist:\n"
                "- No ROWNUM, LIMIT, or OFFSET is used\n"
                "- ORDER BY appears only in the outermost query\n"
                "- TOP n is used when returning limited ordered results\n"
                "- Only columns from the MARKDOWN SCHEMA REFERENCE are used\n"
                "- All GROUP BY rules are satisfied\n"
                "- JOINs use correct foreign key relationships from schema\n"
                "- Table names: transaction, transactionLine (canonical names)\n"
                "- Primary key is T.id, FK is TL.transaction\n"
                "- Transaction type uses T.type (not transaction_type)\n"
                "- Posting filter uses T.posting = 'T' (not is_non_posting)\n"
                "If any rule is violated, revise the SQL until all checks pass."
            )
        },
        {
            "type": "text",
            "text": (
                "OUTPUT RULES:\n"
                "- Output executable SQL only\n"
                "- Do not include semicolons at the end\n"
                "- Do not explain the SQL unless explicitly asked\n"
                "- Prioritize correctness and SuiteAnalytics compatibility over brevity"
            )
        }
    ]

    # Combine all system text into one system message
    system_content = "\n\n".join([msg["text"] for msg in system_messages])

    # Build schema context with priority: live schema > CSV schema > markdown schema > fallback
    schema_parts = []
    
    # 1. Live schema from OA_TABLES/OA_COLUMNS (highest priority - actual database)
    if live_schema:
        schema_parts.append(live_schema)
    
    # 2. CSV allowed schema (curated list)
    allowed_schema = _load_allowed_schema()
    if allowed_schema:
        schema_parts.append(allowed_schema)
    
    # 3. Markdown schema reference (detailed documentation)
    md_schema = _load_markdown_schema()
    if md_schema:
        schema_parts.append(md_schema)
    
    # 4. Fallback to hardcoded schema if nothing else available
    if not schema_parts:
        schema_parts.append(NETSUITE_SCHEMA)
    
    schema = "\n\n".join(schema_parts)

    kb_text = f"\n\n{kb_context}\n" if kb_context else ""
    schema_hint_text = f"\n\nSCHEMA HINT:\n{schema_hint}" if schema_hint else ""
    user = (
        f"{schema}\n\n"
        f"{kb_text}"
        f"{schema_hint_text}"
        f"\n\nUser request: {prompt}\n\n"
        "Generate a SuiteAnalytics Connect SQL query. No semicolon at the end."
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user},
        ],
        **_get_completion_kwargs(max_tokens),
    )

    logger.info(f"SQL generation response: finish_reason={response.choices[0].finish_reason}")
    
    content = (response.choices[0].message.content or "").strip()
    
    # Clean up markdown code fences if present
    if content.startswith("```sql"):
        content = content[6:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    if not content:
        # Log more details for debugging
        logger.error(f"LLM returned empty response. Model: {settings.openai_model}, "
                    f"finish_reason: {response.choices[0].finish_reason}, "
                    f"prompt length: {len(user)}")
        raise LlmError("LLM returned empty response - the model may not have generated SQL for this query")

    return SqlGenerationResult(sql=content, model=settings.openai_model)

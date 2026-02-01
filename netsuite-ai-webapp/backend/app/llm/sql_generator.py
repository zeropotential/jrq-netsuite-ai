from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from app.core.config import settings
from app.llm.netsuite_schema import NETSUITE_SCHEMA

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

    lines = ["ALLOWED TABLES AND COLUMNS (ONLY USE THESE):"]
    for table in sorted(table_map):
        cols = ", ".join(sorted(table_map[table]))
        lines.append(f"{table}:\n  {cols}")
    return "\n".join(lines)


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
) -> SqlGenerationResult:
    if settings.llm_provider.lower() != "openai":
        raise LlmError("Unsupported LLM provider")

    client = _require_openai_client(api_key)

    # Build system messages for SuiteAnalytics Connect SQL expert
    system_messages = [
        {
            "type": "text",
            "text": "You are an expert in NetSuite SuiteAnalytics Connect (JDBC) SQL. All SQL you generate must be valid for the NetSuite OpenAccess SQL engine and executable without modification."
        },
        {
            "type": "text",
            "text": "SCHEMA RESTRICTION: You MUST ONLY use tables and columns listed in the allowed schema below. Do not use any other tables or columns."
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
                "TRANSACTION AND LINE RULES:\n"
                "1. When querying TRANSACTIONLINE, always include TL.MAINLINE = 'F'.\n"
                "2. Never aggregate TRANSACTIONLINE data without filtering MAINLINE.\n"
                "3. If T.POSTING = 'T' is used, only include posting transaction types (e.g., Invoice, Cash Sale). Do not include non-posting types such as Sales Order unless explicitly required.\n"
                "4. Use valid JDBC columns only. Do not invent or assume columns.\n"
                "5. Invalid example: TL.AMOUNT. Valid examples: TL.NETAMOUNT, TL.FOREIGNAMOUNT, TL.QUANTITY, TL.RATE."
            )
        },
        {
            "type": "text",
            "text": (
                "DATES, NULLS, AND AGGREGATION:\n"
                "1. Use TO_DATE('YYYY-MM-DD','YYYY-MM-DD') for date comparisons.\n"
                "2. Use COALESCE() for null handling.\n"
                "3. Every non-aggregated column in SELECT must appear in GROUP BY.\n"
                "4. Prefer TL.NETAMOUNT for revenue calculations.\n"
                "5. Always use table aliases and fully qualify column references."
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
                "- Aggregation without TL.MAINLINE = 'F'\n"
                "- Wrapping a query solely to apply ORDER BY or limits"
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
                "- TL.MAINLINE = 'F' is present when TRANSACTIONLINE is used\n"
                "- Only valid SuiteAnalytics JDBC columns are referenced\n"
                "- All GROUP BY rules are satisfied\n"
                "- Transaction posting logic is consistent with T.POSTING usage\n"
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

    # Use CSV allowed schema if present, else fall back
    allowed_schema = _load_allowed_schema()
    schema = allowed_schema or NETSUITE_SCHEMA

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
    if not content:
        # Log more details for debugging
        logger.error(f"LLM returned empty response. Model: {settings.openai_model}, "
                    f"finish_reason: {response.choices[0].finish_reason}, "
                    f"prompt length: {len(user)}")
        raise LlmError("LLM returned empty response - the model may not have generated SQL for this query")

    return SqlGenerationResult(sql=content, model=settings.openai_model)

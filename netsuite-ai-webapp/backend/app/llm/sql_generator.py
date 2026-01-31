from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings
from app.llm.netsuite_schema import NETSUITE_SCHEMA

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


@dataclass(frozen=True)
class SqlGenerationResult:
    sql: str
    model: str


def _require_openai_client(api_key: str | None) -> OpenAI:
    key = api_key or settings.openai_api_key
    if not key:
        raise LlmError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=key)


def _get_completion_kwargs(max_tokens: int) -> dict:
    """Return the appropriate token limit parameter based on model."""
    model = settings.openai_model.lower()
    # GPT-5 series uses max_completion_tokens
    if "gpt-5" in model or "o1" in model or "o3" in model:
        return {"max_completion_tokens": max_tokens}
    # Older models use max_tokens
    return {"max_tokens": max_tokens}


def generate_oracle_sql(
    *,
    prompt: str,
    schema_hint: str | None = None,
    max_tokens: int = 800,
    api_key: str | None = None,
) -> SqlGenerationResult:
    if settings.llm_provider.lower() != "openai":
        raise LlmError("Unsupported LLM provider")

    client = _require_openai_client(api_key)

    system = (
        "You are a SQL-92 compliant SQL generator for NetSuite SuiteAnalytics Connect (ODBC/JDBC). "
        "Return ONLY a single SQL SELECT statement with NO semicolon at the end. "
        "Never return explanations, markdown, or code fences. "
        "Use ONLY SELECT statements (WITH/CTE is allowed). "
        "\n\nCRITICAL SQL-92 RULES:\n"
        "- Use standard SQL-92 syntax only\n"
        "- Use INNER JOIN, LEFT JOIN, RIGHT JOIN (not implicit joins)\n"
        "- For row limits: wrap query as SELECT * FROM (subquery) WHERE ROWNUM <= N\n"
        "- String literals use single quotes: 'value'\n"
        "- Use IS NULL / IS NOT NULL for null checks\n"
        "- Date format: TO_DATE('2024-01-01', 'YYYY-MM-DD')\n"
        "- Boolean fields: 'T' = true, 'F' = false\n"
        "- NO semicolons, NO FETCH FIRST, NO LIMIT clause\n"
        "- For aggregations (COUNT, SUM, AVG, MIN, MAX) without GROUP BY, do NOT add ROWNUM\n"
    )

    # Use the full schema from the Excel file, or fall back to provided hint
    schema = schema_hint if schema_hint else NETSUITE_SCHEMA

    user = (
        f"{schema}\n\n"
        f"User request: {prompt}\n\n"
        "Generate a SQL-92 compliant SELECT statement for NetSuite. No semicolon at the end."
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        **_get_completion_kwargs(max_tokens),
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise LlmError("LLM returned empty response")

    return SqlGenerationResult(sql=content, model=settings.openai_model)

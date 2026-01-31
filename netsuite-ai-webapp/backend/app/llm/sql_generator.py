from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings


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


def generate_oracle_sql(
    *,
    prompt: str,
    schema_hint: str | None = None,
    max_tokens: int = 400,
    api_key: str | None = None,
) -> SqlGenerationResult:
    if settings.llm_provider.lower() != "openai":
        raise LlmError("Unsupported LLM provider")

    client = _require_openai_client(api_key)

    system = (
        "You are a SQL generator for Oracle SQL used by NetSuite SuiteAnalytics Connect. "
        "Return ONLY a single SQL SELECT statement. "
        "Never return explanations, markdown, or code fences. "
        "Use ONLY SELECT or WITH statements."
    )

    schema = f"Schema hint: {schema_hint}" if schema_hint else "No schema hint provided."

    user = (
        f"{schema}\n"
        "Task: Translate the user request into Oracle SQL."
        f"\nUser request: {prompt}\n"
        "Constraints: SELECT-only; avoid DML/DDL; limit results with FETCH FIRST 50 ROWS ONLY if no limit."
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise LlmError("LLM returned empty response")

    return SqlGenerationResult(sql=content, model=settings.openai_model)

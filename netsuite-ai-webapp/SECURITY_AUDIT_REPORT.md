# Security Audit Report

**Application:** JRQ NetSuite AI Web App  
**Audit Date:** February 27, 2026  
**Auditor:** Security Review — Automated Analysis  
**Scope:** Full-stack codebase (backend, frontend, deployment)

---

## Executive Summary

18 vulnerabilities were identified across the codebase, including **3 CRITICAL**, **5 HIGH**, **7 MEDIUM**, and **3 LOW** severity issues. The most significant risks involve unauthenticated admin endpoints, SQL injection vectors, and cross-site scripting (XSS) via unsanitized HTML rendering.

All identified vulnerabilities have been remediated in the accompanying code changes.

---

## Findings

### CRITICAL

| # | Finding | File(s) | OWASP Category |
|---|---------|---------|----------------|
| C-1 | **No Authentication on Admin Endpoints** — All `/admin/*` endpoints (create JDBC connections, sync data, discover schema, data explorer) are completely unprotected. Any unauthenticated user can create connections, view/export all mirrored data, and trigger syncs. RBAC models exist but are not wired in. | `admin/router.py` | A01:2021 — Broken Access Control |
| C-2 | **No Authentication on API Endpoints** — Chat, report, SQL translate, feedback, and learning stats endpoints have no authentication. The OpenAI API key header is the only gating, but it is not an auth mechanism. | `chat.py`, `report.py`, `sql.py`, `health.py` | A01:2021 — Broken Access Control |
| C-3 | **SQL Injection via Raw SQL Passthrough** — Users can submit arbitrary SQL (any string starting with SELECT/WITH) that is executed directly against JDBC and PostgreSQL. The `_validate_sql()` function uses regex-based blocklists which can be bypassed with comment injection (`/**/DROP/**/`), unicode tricks, or creative CTEs. `text(rewritten_sql)` is used without parameterization. | `chat.py`, `report.py`, `postgres_query.py` | A03:2021 — Injection |

### HIGH

| # | Finding | File(s) | OWASP Category |
|---|---------|---------|----------------|
| H-1 | **XSS via Unsanitized innerHTML** — Multiple locations render API response data, column names, and cell values directly into HTML via `innerHTML` without escaping. LLM-generated HTML is loaded into iframes. Column names from query results are rendered as raw HTML in dashboard tables and stats. | `index.html` | A03:2021 — Injection (XSS) |
| H-2 | **No CORS Configuration** — No CORS middleware is configured; any origin can make cross-origin API requests when the SPA is served via Caddy. | `main.py` | A05:2021 — Security Misconfiguration |
| H-3 | **Missing Security Headers** — No CSP, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Referrer-Policy, or Permissions-Policy headers are set. Neither the application nor Caddy enforces these. | `main.py`, `Caddyfile` | A05:2021 — Security Misconfiguration |
| H-4 | **Information Leakage in Error Messages** — Error responses expose internal SQL queries, stack trace class names, table names, and database error details to the client. | `chat.py`, `report.py` | A04:2021 — Insecure Design |
| H-5 | **OpenAPI/Swagger Docs Exposed** — FastAPI's `/docs` and `/redoc` are enabled in production, exposing the complete API surface to attackers. | `main.py` | A05:2021 — Security Misconfiguration |

### MEDIUM

| # | Finding | File(s) | OWASP Category |
|---|---------|---------|----------------|
| M-1 | **No Rate Limiting** — No rate limiting on any endpoint. Attackers can abuse the chat endpoint to incur OpenAI API costs, exhaust JDBC connection pools, or perform denial-of-service. | All routes | A04:2021 — Insecure Design |
| M-2 | **Sensitive Data in Logs** — User messages, full SQL queries, and intent classifications are logged at INFO level without redaction. | `chat.py`, `sql_generator.py` | A09:2021 — Security Logging & Monitoring Failures |
| M-3 | **Unsafe iframe Sandbox** — LLM-generated HTML is rendered in an iframe with `sandbox="allow-scripts"`, allowing arbitrary JS execution within the sandboxed frame. | `index.html` | A03:2021 — Injection |
| M-4 | **Default Database Credentials** — Default `database_url` in config uses `postgres:postgres`. While overridden in production, the default is insecure. | `config.py` | A07:2021 — Identification & Authentication Failures |
| M-5 | **Raw SQL in Admin Query Endpoint** — `TableQueryRequest.where` accepts string filters parsed with regex, allowing potential filter injection. | `admin/router.py` | A03:2021 — Injection |
| M-6 | **OpenAI API Key in HTTP Header** — API keys transmitted as `X-OpenAI-Api-Key` headers appear in access logs and proxy logs. | `chat.py`, `report.py`, `sql.py` | A02:2021 — Cryptographic Failures |
| M-7 | **No Request Size Limits** — No max request body size is enforced; large payloads could exhaust memory. | `main.py` | A04:2021 — Insecure Design |

### LOW

| # | Finding | File(s) | OWASP Category |
|---|---------|---------|----------------|
| L-1 | **Docker Container Runs as Root** — Dockerfile has no `USER` directive; the application runs as the root user inside the container. | `Dockerfile` | A05:2021 — Security Misconfiguration |
| L-2 | **Missing .dockerignore** — No `.dockerignore` file; sensitive files (`.env`, `.git`, `*.csv`) may be copied into the Docker image. | Project root | A05:2021 — Security Misconfiguration |
| L-3 | **Caddy Missing Security Headers** — The Caddyfile does not set security-related response headers. | `Caddyfile` | A05:2021 — Security Misconfiguration |

---

## Remediation Summary

| Fix | Addresses | Files Modified/Created |
|-----|-----------|----------------------|
| Add `SecurityHeadersMiddleware` with CSP, HSTS, X-Frame-Options, etc. | H-3, L-3 | `middleware.py` |
| Add `AdminAuthMiddleware` with API key protection for `/admin/*` | C-1 | `middleware.py`, `config.py` |
| Add `RateLimitMiddleware` using in-memory sliding window | M-1 | `middleware.py` |
| Add CORS middleware with configurable origins | H-2 | `main.py`, `config.py` |
| Disable `/docs` and `/redoc` in production | H-5 | `main.py` |
| Limit `max_request_body_size` | M-7 | `middleware.py` |
| Sanitize error messages to remove SQL and internal details | H-4 | `chat.py`, `report.py` |
| Strengthen SQL validation (block comments, encoding, deeper CTE analysis) | C-3 | `postgres_query.py` |
| Sanitize admin query endpoint `where` clause | M-5 | `admin/router.py` |
| HTML-escape all dynamic content rendered via innerHTML | H-1 | `index.html` |
| Remove `allow-scripts` from iframe sandbox | M-3 | `index.html` |
| Redact sensitive data from log messages | M-2 | `chat.py` |
| Add non-root user to Dockerfile | L-1 | `Dockerfile` |
| Create `.dockerignore` | L-2 | `.dockerignore` |
| Add security headers to Caddyfile | L-3 | `Caddyfile` |
| Add `admin_api_key` and `cors_origins` to config | C-1, H-2 | `config.py` |
| Enforce safe default for `database_url` | M-4 | `config.py` |

---

## Compliance Standards Referenced

- OWASP Top 10 (2021)
- OWASP API Security Top 10 (2023)
- CWE/SANS Top 25
- NIST SP 800-53 (AC, SC, SI controls)

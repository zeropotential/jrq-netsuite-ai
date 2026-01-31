# NetSuite AI Web App (FastAPI + Docker Compose)

This repository scaffolds a Hostinger-VPS-ready FastAPI app intended to:
- Query NetSuite SuiteAnalytics Connect via JDBC for SQL-based reporting/chat answers
- Create transactions via SuiteTalk/RESTlet (starting with Journal Entries)
- Store JDBC credentials encrypted in Postgres
- Maintain full session/prompt/audit logging
- Enforce a strict **no-deletions** policy by design

## Quickstart (Docker)

From the repository root:

```bash
cd netsuite-ai-webapp
cp deploy/compose/.env.example deploy/compose/.env
docker compose -f deploy/compose/docker-compose.yml up --build
```

Then open:
- `http://localhost/healthz`
- `http://localhost/readyz`
- `http://localhost:8000/` (basic chat UI)

## Notes
- The NetSuite JDBC driver JAR is **not included**. When we implement JDBC, you will mount it at runtime.
- This is an initial scaffold; authentication, RBAC, admin UI, JDBC querying, and NetSuite write flows will be built next.

## UI status
This scaffold includes a minimal chat UI served from `/` by the API service. The UI posts to `/api/chat` which now runs NetSuite JDBC SELECT queries.

## NetSuite JDBC (implemented)
The `/api/chat` endpoint now executes **SELECT-only** SQL against NetSuite via JDBC. Provide:
- `connection_id` created from `/admin/jdbc-connections`
- `message` containing the SQL query

Required env:
- `NETSUITE_JDBC_JAR` (path to the NetSuite JDBC driver JAR; mounted into the container)
- `NETSUITE_JDBC_DRIVER` (defaults to `com.netsuite.jdbc.OpenAccessDriver`)

Example chat payload:
```
{
	"connection_id": "<uuid>",
	"message": "SELECT * FROM transaction LIMIT 5"
}
```

## LLM SQL translation (Oracle)
Natural language is translated to Oracle SQL using the configured LLM. The chat endpoint now accepts plain English prompts and returns the generated SQL in the response. You can also call `/api/sql/translate` directly.

Required env:
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

## Dashboards & reports
Use `/api/report/run` to run a report and `/api/report/export/{csv|xlsx|pdf}` to export. The built-in UI exposes Run/Export actions for quick dashboards.

## Hostinger VPS deployment (Docker Compose)
1. **Provision VPS** (Ubuntu 22.04+), open ports **80/443** in Hostinger firewall.
2. **Install Docker + Compose** on the VPS.
3. **Clone the repo** and copy env file:
	- `cp deploy/compose/.env.example deploy/compose/.env`
4. **Update env values** in `deploy/compose/.env`:
	- `PUBLIC_HOST=your-domain.com`
	- `APP_KEK_B64` (base64 32-byte key)
	- Database credentials, etc.
5. **Launch**:
	- `docker compose -f deploy/compose/docker-compose.yml up --build -d`
6. **Point DNS** for your domain to the VPS IP.
7. **Verify**:
	- `https://your-domain.com/` (UI)
	- `https://your-domain.com/healthz`

If you prefer to run without Caddy, remove the `caddy` service and expose `api` directly; update firewall/DNS accordingly.

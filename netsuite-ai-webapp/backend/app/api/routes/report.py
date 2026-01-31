from __future__ import annotations

import csv
import io
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.llm.sql_generator import LlmError, generate_oracle_sql
from app.netsuite.jdbc import JdbcError, run_query

router = APIRouter(prefix="/api/report", tags=["report"])


class ReportRequest(BaseModel):
    connection_id: str
    prompt: str | None = None
    sql: str | None = None
    schema_hint: str | None = None


class ReportResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[str]]


def _normalize_sql(sql: str) -> str:
    normalized = sql.lower().lstrip()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    return sql


def _ensure_limit(sql: str) -> str:
    lowered = sql.lower()
    if " fetch first " in lowered or " limit " in lowered:
        return sql
    return f"{sql.rstrip(';')} FETCH FIRST {settings.netsuite_jdbc_row_limit} ROWS ONLY"


def _run_report(db: Session, payload: ReportRequest) -> tuple[str, list[str], list[list[str]]]:
    sql = payload.sql
    if not sql:
        if not payload.prompt:
            raise HTTPException(status_code=400, detail="prompt or sql is required")
        try:
            result = generate_oracle_sql(prompt=payload.prompt, schema_hint=payload.schema_hint)
        except LlmError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sql = result.sql

    sql = _normalize_sql(sql)
    sql = _ensure_limit(sql)

    try:
        result = run_query(db, payload.connection_id, sql, settings.netsuite_jdbc_row_limit)
    except JdbcError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="JDBC query failed") from exc

    columns = result.get("columns", [])
    rows = [list(map(lambda value: "" if value is None else str(value), row)) for row in result.get("rows", [])]
    return sql, columns, rows


@router.post("/run", response_model=ReportResponse)
def run_report(payload: ReportRequest, db: Session = Depends(get_db)) -> ReportResponse:
    sql, columns, rows = _run_report(db, payload)
    return ReportResponse(sql=sql, columns=columns, rows=rows)


@router.post("/export/csv")
def export_csv(payload: ReportRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    sql, columns, rows = _run_report(db, payload)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if columns:
        writer.writerow(columns)
    writer.writerows(rows)

    filename = "report.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/export/xlsx")
def export_xlsx(payload: ReportRequest, db: Session = Depends(get_db)) -> Response:
    from openpyxl import Workbook

    sql, columns, rows = _run_report(db, payload)

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    if columns:
        ws.append(columns)
    for row in rows:
        ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=report.xlsx"},
    )


@router.post("/export/pdf")
def export_pdf(payload: ReportRequest, db: Session = Depends(get_db)) -> Response:
    sql, columns, rows = _run_report(db, payload)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    x = 40
    y = height - 40

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "NetSuite Report")
    y -= 20

    pdf.setFont("Helvetica", 9)
    pdf.drawString(x, y, f"SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
    y -= 20

    if columns:
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x, y, " | ".join(columns))
        y -= 14

    pdf.setFont("Helvetica", 8)
    for row in rows:
        pdf.drawString(x, y, " | ".join(row))
        y -= 12
        if y < 40:
            pdf.showPage()
            y = height - 40
            pdf.setFont("Helvetica", 8)

    pdf.save()
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"},
    )

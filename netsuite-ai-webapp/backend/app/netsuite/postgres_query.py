"""
Execute SQL queries against the local PostgreSQL mirror tables.

This provides fast query execution for NetSuite data that has been
synced to local PostgreSQL.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Allowed tables for querying (prevent SQL injection)
ALLOWED_TABLES = {
    "ns_account",
    "ns_transaction", 
    "ns_transactionline",
    # Aliases that map to real tables
    "account": "ns_account",
    "transaction": "ns_transaction",
    "transactionline": "ns_transactionline",
}


def _rewrite_table_names(sql: str) -> str:
    """
    Rewrite table names from NetSuite canonical names to PostgreSQL mirror names.
    
    Maps:
    - account -> ns_account
    - transaction -> ns_transaction
    - transactionline -> ns_transactionline
    """
    # Replace table names (case-insensitive, word boundaries)
    # Order matters - do transactionline before transaction
    replacements = [
        (r'\btransactionline\b', 'ns_transactionline'),
        (r'\btransactionLine\b', 'ns_transactionline'),
        (r'\bTransactionLine\b', 'ns_transactionline'),
        (r'\btransaction\b', 'ns_transaction'),
        (r'\bTransaction\b', 'ns_transaction'),
        (r'\baccount\b', 'ns_account'),
        (r'\bAccount\b', 'ns_account'),
    ]
    
    result = sql
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def _rewrite_syntax(sql: str) -> str:
    """
    Rewrite NetSuite-specific SQL syntax to PostgreSQL.
    
    - TOP N -> LIMIT N
    - TO_DATE(...) -> already works in PostgreSQL
    """
    # Convert TOP N to LIMIT N
    # Pattern: SELECT TOP 10 ... -> SELECT ... LIMIT 10
    top_pattern = r'SELECT\s+TOP\s+(\d+)\s+'
    match = re.search(top_pattern, sql, re.IGNORECASE)
    if match:
        limit_val = match.group(1)
        # Remove TOP N and add LIMIT N at the end
        sql = re.sub(top_pattern, 'SELECT ', sql, flags=re.IGNORECASE)
        # Add LIMIT before any trailing semicolon
        sql = sql.rstrip(';').strip()
        sql = f"{sql} LIMIT {limit_val}"
    
    return sql


def _validate_sql(sql: str) -> None:
    """
    Basic SQL validation to prevent dangerous operations.
    """
    sql_upper = sql.upper().strip()
    
    # Only allow SELECT
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    
    # Block dangerous keywords
    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"]
    for keyword in dangerous:
        if re.search(rf'\b{keyword}\b', sql_upper):
            raise ValueError(f"Dangerous keyword not allowed: {keyword}")


def execute_postgres_query(
    db: Session,
    sql: str,
    limit: int = 1000,
) -> dict[str, Any]:
    """
    Execute a SQL query against the PostgreSQL mirror tables.
    
    Args:
        db: Database session
        sql: SQL query (can use NetSuite table names - will be rewritten)
        limit: Maximum rows to return
    
    Returns:
        dict with columns and rows
    """
    # Validate
    _validate_sql(sql)
    
    # Rewrite table names and syntax
    rewritten_sql = _rewrite_table_names(sql)
    rewritten_sql = _rewrite_syntax(rewritten_sql)
    
    logger.info(f"Executing PostgreSQL query: {rewritten_sql[:200]}...")
    
    try:
        result = db.execute(text(rewritten_sql))
        
        # Get column names
        columns = list(result.keys())
        
        # Fetch rows (with limit)
        rows = []
        for i, row in enumerate(result):
            if i >= limit:
                break
            rows.append(list(row))
        
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) >= limit,
            "rewritten_sql": rewritten_sql,
        }
        
    except Exception as e:
        logger.error(f"PostgreSQL query failed: {e}")
        raise ValueError(f"Query execution failed: {e}") from e


def get_postgres_schema() -> str:
    """
    Return schema documentation for PostgreSQL mirror tables.
    
    This is used by the LLM to generate correct SQL.
    """
    return """
## PostgreSQL Mirror Tables Schema

These are local PostgreSQL tables mirrored from NetSuite. Use standard PostgreSQL syntax.

### Table: transaction (alias for ns_transaction)
Primary key: id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | NetSuite internal ID |
| tranid | VARCHAR | Document number (e.g., INV-12345) |
| type | VARCHAR | Transaction type: CustInvc, SalesOrd, VendBill, CustPymt, etc. |
| trandate | TIMESTAMP | Transaction date |
| status | VARCHAR | Transaction status |
| posting | VARCHAR(1) | 'T' for posting, 'F' for non-posting |
| entity | BIGINT | Customer/vendor ID |
| duedate | TIMESTAMP | Due date |
| closedate | TIMESTAMP | Close date |
| createddate | TIMESTAMP | Created date |
| lastmodifieddate | TIMESTAMP | Last modified date |
| foreigntotal | FLOAT | Total in foreign currency |
| currency | BIGINT | Currency ID |
| exchangerate | FLOAT | Exchange rate |
| memo | TEXT | Memo/notes |

### Table: transactionline (alias for ns_transactionline)
Primary key: id
Foreign key: transaction -> ns_transaction.id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Line unique ID |
| transaction | BIGINT | FK to transaction.id |
| linesequencenumber | BIGINT | Line sequence |
| item | BIGINT | Item ID |
| amount | FLOAT | Line amount (use for SUM) |
| netamount | FLOAT | Net amount |
| foreignamount | FLOAT | Amount in foreign currency |
| quantity | FLOAT | Quantity |
| account | BIGINT | Account ID |
| department | BIGINT | Department ID |
| class | BIGINT | Class ID |
| location | BIGINT | Location ID |
| memo | TEXT | Line memo |

### Table: account (alias for ns_account)
Primary key: id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | NetSuite internal ID |
| acctnumber | VARCHAR | Account number |
| name | VARCHAR | Account name |
| fullname | VARCHAR | Full account name (with hierarchy) |
| type | VARCHAR | Account type |
| accttype | VARCHAR | Account type code |
| isinactive | VARCHAR(1) | 'T' if inactive |
| parent | BIGINT | Parent account ID |
| currency | BIGINT | Currency ID |

### JOIN Pattern
```sql
SELECT T.id, T.tranid, T.type, T.trandate, SUM(TL.amount) as total
FROM transaction T
INNER JOIN transactionline TL ON T.id = TL.transaction
WHERE T.type = 'CustInvc' AND T.posting = 'T'
GROUP BY T.id, T.tranid, T.type, T.trandate
```

### SQL Syntax (PostgreSQL)
- Use LIMIT N (not TOP N)
- Dates: Use standard PostgreSQL date syntax or TO_DATE()
- Boolean: 'T' or 'F' strings
- Aggregations: SUM(), COUNT(), AVG() work on numeric columns
"""

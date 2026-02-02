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
    "ns_employee",
    "ns_customer",
}

# Aliases that map to real tables
TABLE_ALIASES = {
    "account": "ns_account",
    "transaction": "ns_transaction",
    "transactionline": "ns_transactionline",
    "employee": "ns_employee",
    "customer": "ns_customer",
}


def _rewrite_table_names(sql: str) -> str:
    """
    Rewrite table names from NetSuite canonical names to PostgreSQL mirror names.
    
    Maps:
    - account -> ns_account
    - transaction -> ns_transaction
    - transactionline -> ns_transactionline
    
    IMPORTANT: Only replace table names, not column references.
    Column references like "TL.transaction" should NOT be rewritten.
    """
    # Only replace table names that appear after FROM, JOIN, INTO, UPDATE, or at start
    # Use negative lookbehind to avoid replacing column references (after a dot)
    # Order matters - do transactionline before transaction
    
    def replace_table_name(sql_text: str, old_name: str, new_name: str) -> str:
        """Replace table name only when it's used as a table, not a column."""
        # Pattern matches table name when:
        # 1. After FROM, JOIN (various types), INTO, UPDATE (case insensitive)
        # 2. NOT preceded by a dot (which would make it a column reference)
        
        # First, handle cases after SQL keywords
        keywords = ['FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'OUTER JOIN', 'CROSS JOIN']
        result = sql_text
        
        for kw in keywords:
            # Pattern: keyword + whitespace + table_name (case insensitive)
            pattern = rf'({kw}\s+)({old_name})(\s|$|\s+[A-Za-z])'
            result = re.sub(pattern, rf'\1{new_name}\3', result, flags=re.IGNORECASE)
        
        return result
    
    result = sql
    
    # Apply replacements - order matters (transactionline before transaction)
    result = replace_table_name(result, 'transactionline', 'ns_transactionline')
    result = replace_table_name(result, 'transaction', 'ns_transaction')
    result = replace_table_name(result, 'account', 'ns_account')
    result = replace_table_name(result, 'employee', 'ns_employee')
    result = replace_table_name(result, 'customer', 'ns_customer')
    
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
    Strict SQL validation to prevent dangerous operations.
    Only allows SELECT queries (including CTEs) on specific tables.
    """
    sql_upper = sql.upper().strip()
    
    # Only allow SELECT or WITH (CTEs that resolve to SELECT)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed")
    
    # If it starts with WITH (CTE), ensure the final statement is SELECT
    if sql_upper.startswith("WITH"):
        # CTEs can be used with INSERT/UPDATE/DELETE, block those
        # The final statement after all CTE definitions must be SELECT
        # Find the main query - look for SELECT that's not inside a CTE definition
        # A simple approach: ensure SELECT appears after the CTE block and no DML keywords
        if re.search(r'\)\s*(INSERT|UPDATE|DELETE|MERGE)\s', sql_upper):
            raise ValueError("Only SELECT queries are allowed (no INSERT/UPDATE/DELETE with CTEs)")
        # Also ensure there's a SELECT in the main query part
        if "SELECT" not in sql_upper:
            raise ValueError("CTE must contain a SELECT query")
    
    # Block dangerous keywords as whole words (comprehensive list)
    # Use word boundary regex to avoid false positives like "create_date"
    # Note: For CTEs, we check the context above, so these keywords in CTE subqueries are ok
    dangerous_words = [
        "DROP", "TRUNCATE", "ALTER", "CREATE", 
        "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "COPY", "LOAD",
    ]
    for keyword in dangerous_words:
        # Match keyword as a whole word (not part of column names like create_date)
        if re.search(rf'\b{keyword}\b', sql_upper):
            raise ValueError(f"Dangerous keyword not allowed: {keyword}")
    
    # For non-CTE queries, also block DML
    if not sql_upper.startswith("WITH"):
        dml_words = ["DELETE", "UPDATE", "INSERT", "MERGE"]
        for keyword in dml_words:
            if re.search(rf'\b{keyword}\b', sql_upper):
                raise ValueError(f"Dangerous keyword not allowed: {keyword}")
    
    # Block dangerous patterns that don't need word boundaries
    dangerous_patterns = [
        "INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE",
        "INFORMATION_SCHEMA", "PG_CATALOG", "PG_USER", "PG_SHADOW",
        ";",  # No multi-statement
    ]
    for pattern in dangerous_patterns:
        if pattern in sql_upper:
            raise ValueError(f"Dangerous pattern not allowed: {pattern}")
    
    # Ensure only allowed tables are queried
    # Extract table names from query (basic pattern matching)
    # Match FROM/JOIN followed by table name
    table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    found_tables = re.findall(table_pattern, sql, re.IGNORECASE)
    
    allowed = {"ns_account", "ns_transaction", "ns_transactionline", "ns_employee", "ns_customer",
               "account", "transaction", "transactionline", "employee", "customer"}
    for table in found_tables:
        if table.lower() not in allowed:
            raise ValueError(f"Table not allowed: {table}. Only NetSuite mirror tables are queryable.")


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

IMPORTANT: You can ONLY query these 5 tables. Always use the ns_ prefix for table names!
If the user asks about data not in these tables, explain what tables ARE available.

### Table: ns_transaction
Primary key: id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | NetSuite internal ID |
| tranid | VARCHAR | Document number (e.g., INV-12345) |
| type | VARCHAR | Transaction type: CustInvc, SalesOrd, VendBill, CustPymt, etc. |
| trandate | TIMESTAMP | Transaction date |
| status | VARCHAR | Transaction status |
| posting | VARCHAR(1) | 'T' for posting, 'F' for non-posting |
| entity | BIGINT | Customer/vendor ID (FK to ns_customer.id) |
| duedate | TIMESTAMP | Due date |
| closedate | TIMESTAMP | Close date |
| createddate | TIMESTAMP | Created date |
| lastmodifieddate | TIMESTAMP | Last modified date |
| foreigntotal | FLOAT | Total in foreign currency |
| currency | BIGINT | Currency ID |
| exchangerate | FLOAT | Exchange rate |
| memo | TEXT | Memo/notes |

### Table: ns_transactionline
Primary key: id
Foreign key: transaction -> ns_transaction.id (NOTE: the column is named 'transaction', not 'ns_transaction')
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Line unique ID |
| transaction | BIGINT | FK to ns_transaction.id (use this for JOINs: TL.transaction = T.id) |
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

### Table: ns_account
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

### Table: ns_employee
Primary key: id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | NetSuite internal ID |
| entityid | VARCHAR | Employee ID/code |
| firstname | VARCHAR | First name |
| lastname | VARCHAR | Last name |
| email | VARCHAR | Email address |
| isinactive | VARCHAR(1) | 'T' if inactive |
| department | BIGINT | Department ID |
| class | BIGINT | Class ID |
| location | BIGINT | Location ID |
| subsidiary | BIGINT | Subsidiary ID |
| supervisor | BIGINT | Supervisor employee ID |
| title | VARCHAR | Job title |
| hiredate | TIMESTAMP | Hire date |
| releasedate | TIMESTAMP | Termination date |

### Table: ns_customer
Primary key: id
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | NetSuite internal ID |
| entityid | VARCHAR | Customer ID/code |
| companyname | VARCHAR | Company name |
| email | VARCHAR | Email address |
| phone | VARCHAR | Phone number |
| isinactive | VARCHAR(1) | 'T' if inactive |
| category | BIGINT | Customer category ID |
| subsidiary | BIGINT | Subsidiary ID |
| salesrep | BIGINT | Sales rep employee ID |
| balance | FLOAT | Account balance |
| creditlimit | FLOAT | Credit limit |
| currency | BIGINT | Currency ID |
| datecreated | TIMESTAMP | Date created |
| lastmodifieddate | TIMESTAMP | Last modified |

### JOIN Patterns (IMPORTANT: note the column vs table names)
```sql
-- Transaction with customer
SELECT T.id, T.tranid, T.type, C.companyname
FROM ns_transaction T
INNER JOIN ns_customer C ON T.entity = C.id
WHERE T.type = 'CustInvc'

-- Transaction with lines (NOTE: column is 'transaction', table is 'ns_transactionline')
SELECT T.id, T.tranid, T.type, T.trandate, SUM(TL.amount) as total
FROM ns_transaction T
INNER JOIN ns_transactionline TL ON T.id = TL.transaction
WHERE T.type = 'CustInvc' AND T.posting = 'T'
GROUP BY T.id, T.tranid, T.type, T.trandate

-- Top customers by sales
SELECT C.id, C.companyname, SUM(TL.amount) as total_sales
FROM ns_transaction T
INNER JOIN ns_transactionline TL ON T.id = TL.transaction
INNER JOIN ns_customer C ON T.entity = C.id
WHERE T.type = 'CustInvc' AND T.posting = 'T'
GROUP BY C.id, C.companyname
ORDER BY total_sales DESC
LIMIT 10
```

### SQL Syntax (PostgreSQL)
- Use LIMIT N (not TOP N)
- Dates: Use standard PostgreSQL date syntax or TO_DATE()
- Boolean: 'T' or 'F' strings
- Aggregations: SUM(), COUNT(), AVG() work on numeric columns

### Available Tables Summary
ONLY these tables exist: ns_account, ns_employee, ns_customer, ns_transaction, ns_transactionline
Always use the ns_ prefix! Do NOT query any other tables - they are not synced.
"""

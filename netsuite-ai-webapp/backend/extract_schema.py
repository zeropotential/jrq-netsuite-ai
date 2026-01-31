#!/usr/bin/env python3
"""Extract NetSuite schema from Excel file and generate schema.py"""
import pandas as pd

xlsx = pd.ExcelFile('NS 2 Schemma.xlsx')

# Get records and fields
df_records = pd.read_excel(xlsx, sheet_name='Records')
df_fields = pd.read_excel(xlsx, sheet_name='Fields')

# Build schema dictionary: table -> [columns]
schema = {}
for _, row in df_fields.iterrows():
    table = str(row['Record Name in NetSuite2.com']).strip() if pd.notna(row['Record Name in NetSuite2.com']) else None
    field = str(row['Field ID in NetSuite2.com']).strip() if pd.notna(row['Field ID in NetSuite2.com']) else None
    if table and field and table != 'nan':
        table_upper = table.upper()
        if table_upper not in schema:
            schema[table_upper] = []
        if field.upper() not in schema[table_upper]:
            schema[table_upper].append(field.upper())

print(f"Total tables: {len(schema)}")

# Generate Python schema file
output = '''"""
NetSuite SuiteAnalytics Connect (NS2) Schema
Auto-generated from NS 2 Schemma.xlsx
Use SQL-92 standard syntax with these tables and columns.
"""

NETSUITE_SCHEMA = """
NetSuite SuiteAnalytics Connect (NS2) Database Schema
======================================================
Use SQL-92 standard syntax. Table and column names are case-insensitive.

IMPORTANT SQL-92 RULES:
- Use standard JOINs: INNER JOIN, LEFT JOIN, RIGHT JOIN
- For row limits, wrap query: SELECT * FROM (your_query) WHERE ROWNUM <= N
- Use single quotes for strings: WHERE status = 'Active'
- Use IS NULL / IS NOT NULL for null checks
- Date format: TO_DATE('2024-01-01', 'YYYY-MM-DD')
- Boolean fields use 'T' for true and 'F' for false

TABLES AND COLUMNS:
'''

# Important tables first with full columns
important = ['EMPLOYEE', 'CUSTOMER', 'VENDOR', 'TRANSACTION', 'TRANSACTIONLINE', 
             'ITEM', 'ACCOUNT', 'SUBSIDIARY', 'DEPARTMENT', 'LOCATION', 'CONTACT', 'ENTITY',
             'JOB', 'SALESREP', 'CURRENCY', 'COUNTRY']

for table in important:
    if table in schema:
        cols = schema[table]
        output += f"\n{table}:\n  {', '.join(cols)}\n"

output += "\nOTHER AVAILABLE TABLES:\n"

# Other tables with abbreviated columns
for table in sorted(schema.keys()):
    if table not in important:
        cols = schema[table][:20]  # First 20 columns
        suffix = ", ..." if len(schema[table]) > 20 else ""
        output += f"\n{table}:\n  {', '.join(cols)}{suffix}\n"

output += '"""'

# Write to file
with open('app/llm/netsuite_schema.py', 'w') as f:
    f.write(output)

print("Generated app/llm/netsuite_schema.py")

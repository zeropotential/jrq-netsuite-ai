# NetSuite SuiteAnalytics Connect Schema Reference (transaction)

This document is a **human-readable schema guide** for the NetSuite SuiteAnalytics Connect (JDBC) **Transactions** record and related browsing links. Use it as authoritative reference for column names and relationships.

## LLM Canonical Table Names (Authoritative Contract)

Use **only** these canonical table names in generated SQL:

- **transaction** (header) → NetSuite table: **Transactions**
- **transactionLine** (line) → NetSuite table: **Transaction_lines**
- **Account** → NetSuite table: **Accounts**

Do **not** use the raw NetSuite table names in generated SQL. Use the column names exactly as listed below, but always attach them to the canonical table names above.

## SQL Syntax Rules (CRITICAL)

- **Use TOP N for limiting results** - NetSuite SuiteAnalytics Connect uses TOP syntax:
  ```sql
  SELECT TOP 100 * FROM transaction
  ```
- **DO NOT use ROWNUM** - Oracle's ROWNUM is NOT supported
- **DO NOT use FETCH FIRST** - Standard SQL FETCH FIRST is NOT supported
- **DO NOT use LIMIT** - MySQL/PostgreSQL LIMIT is NOT supported
- **Use standard SQL-92 syntax** - JOINs, WHERE, GROUP BY, ORDER BY
- **Date format**: Use `TO_DATE('2024-01-01', 'YYYY-MM-DD')` for date literals
- **Boolean fields**: Use `'T'` for true, `'F'` for false
- **String literals**: Use single quotes `'value'`

## Column Naming Convention (CRITICAL - LIVE DATABASE)

**The LIVE NetSuite database uses NO UNDERSCORES in column names.** The documentation shows underscores but the actual JDBC/Connect columns are all lowercase without underscores.

### Common Column Name Mappings (Documentation → LIVE):
| Documentation Name | LIVE Column Name | Notes |
|-------------------|-----------------|-------|
| transaction_id | **id** | Primary key is just "id" |
| transaction_type | **type** | Use "type" not "transaction_type" |
| trandate | trandate | Same |
| is_non_posting | **posting** | Use `posting = 'T'` for posting transactions |
| entity_id | entity | Use "entity" for customer/vendor |
| account_id | account | Use "account" for account reference |

### TransactionLine FK Reference:
- To join transaction to transactionLine: `T.id = TL.transaction`
- The FK column in transactionLine is just `transaction` (not `transaction_id`)

### Amount Columns in transactionLine (CRITICAL):
When working with amounts, use these NUMERIC columns from transactionLine:
| Column | Type | Description |
|--------|------|-------------|
| amount | NUMBER | Line amount (use for SUM) |
| foreignamount | NUMBER | Amount in foreign currency |
| creditforeignamount | NUMBER | Credit amount in foreign currency |
| debitforeignamount | NUMBER | Debit amount in foreign currency |

**DO NOT use `netamount`** - it may not exist or may not be numeric.
**For invoice totals**: Use `SUM(TL.amount)` instead of `SUM(TL.netamount)`

### Example: Top 10 Invoices by Amount
```sql
SELECT TOP 10
  T.id,
  T.tranid,
  T.trandate,
  T.type,
  SUM(TL.amount) AS invoice_total
FROM transaction T
INNER JOIN transactionLine TL ON T.id = TL.transaction
WHERE T.type = 'CustInvc'
  AND T.posting = 'T'
  AND T.trandate >= TO_DATE('2025-12-01','YYYY-MM-DD')
  AND T.trandate <= TO_DATE('2025-12-31','YYYY-MM-DD')
GROUP BY T.id, T.tranid, T.trandate, T.type
ORDER BY invoice_total DESC
```

### Transaction Type Values (CRITICAL):
When filtering by transaction type, use the `type` column with these values:
| Type Value | Description |
|-----------|-------------|
| CustInvc | Customer Invoice |
| CustCred | Credit Memo |
| CustPymt | Customer Payment |
| SalesOrd | Sales Order |
| PurchOrd | Purchase Order |
| VendBill | Vendor Bill |
| VendCred | Vendor Credit |
| VendPymt | Vendor Payment |
| Journal | Journal Entry |
| CashSale | Cash Sale |
| Estimate | Quote/Estimate |
| Opportunity | Opportunity |
| ItemShip | Item Fulfillment |
| ItemRcpt | Item Receipt |

### Example Correct SQL:
```sql
-- Count invoices in 2025
SELECT COUNT(DISTINCT T.id) AS invoice_count
FROM transaction T
INNER JOIN transactionLine TL ON T.id = TL.transaction
WHERE T.type = 'CustInvc'
  AND T.trandate >= TO_DATE('2025-01-01','YYYY-MM-DD')
  AND T.trandate <= TO_DATE('2025-12-31','YYYY-MM-DD')
  AND T.posting = 'T'
```

## Browsers and Reference Links

- Schema Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#schematab
- Records Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#scripttab
- Connect Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#browsertab
- Analytics Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#analyticstab

Additional navigation links:
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/schema/index.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/script/record/transaction.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/analytics/index.html

## Transactions Table – Key Notes

- The **Transaction Body Fields** custom field is available for the **transaction** table (NetSuite: **Transactions**).
- **Credit and debit amounts are NOT exposed** as columns in **transaction**. Use **transactionLine** to obtain credit and debit amounts.
  - More info: https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_4400769955
- **Item count and quantity are NOT exposed** as columns in **transaction**. Use **transactionLine** for quantities.
  - More info: https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_1512507697

## Transactions – Columns

| Name | Type | Length | Precision | Scale | References | In | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| account_based_number | VARCHAR2 | 138 |  |  |  |  | Account based number |
| accounting_book_id | NUMBER |  | 39 | 0 |  |  | Accounting book ID |
| accounting_period_id | NUMBER |  | 39 | 0 |  |  | Accounting period ID |
| acct_corp_card_expenses_id | NUMBER |  | 39 | 0 | account_id | Accounts | ID of the account for corporate card in expense report |
| amount_unbilled | NUMBER |  | 20 | 2 |  |  | Amount unbilled |
| bill_pay_transaction | VARCHAR2 | 3 |  |  |  |  | Bill pay transaction |
| billaddress | VARCHAR2 | 999 |  |  |  |  | Billing address |
| billing_account_id | NUMBER |  | 39 | 0 |  |  | Billing account ID |
| billing_instructions | VARCHAR2 | 999 |  |  |  |  | Billing instructions |
| buildable | NUMBER |  | 39 | 0 |  |  | The number of assemblies that can be built with the current supplies. |
| bulk_submission_id | NUMBER |  | 39 | 0 |  |  | Bulk submission ID |
| carrier | VARCHAR2 | 100 |  |  |  |  | Carrier |
| closed | TIMESTAMP |  |  |  |  |  | Closed |
| company_status_id | NUMBER |  | 39 | 0 |  |  | Company status ID |
| contract_cost_amount | NUMBER |  | 20 | 2 |  |  | Contract cost amount |
| contract_defer_expense_acct_id | NUMBER |  | 39 | 0 |  |  | Contract defer expense account ID |
| contract_expense_acct_id | NUMBER |  | 39 | 0 |  |  | Contract expense account ID |
| contract_expense_src_acct_id | NUMBER |  | 39 | 0 |  |  | Contract acquisition expense source account |
| create_date | TIMESTAMP |  |  |  |  |  | Creation date (GMT) |
| created_by_id | NUMBER |  | 39 | 0 |  |  | ID of the creator |
| created_from_id | NUMBER |  | 39 | 0 |  |  | Created from ID |
| currency_id | NUMBER |  | 39 | 0 |  |  | Currency ID |
| custom_form_id | NUMBER |  | 39 | 0 |  |  | Custom form ID |
| date_actual_prod_end | TIMESTAMP |  |  |  |  |  | The date production ends. |
| date_actual_prod_start | TIMESTAMP |  |  |  |  |  | The date production starts. |
| date_as_of | TIMESTAMP |  |  |  |  |  | As of date |
| date_bid_close | TIMESTAMP |  |  |  |  |  | Bid close date |
| date_bid_open | TIMESTAMP |  |  |  |  |  | Bid open date |
| date_contract_cost_accrual | TIMESTAMP |  |  |  |  |  | Date contract cost accrual |
| date_last_modified | TIMESTAMP |  |  |  |  |  | Date last modified (GMT) |
| date_tax_point | TIMESTAMP |  |  |  |  |  | Transaction date determining taxability rules |
| due_date | TIMESTAMP |  |  |  |  |  | Due date |
| email | VARCHAR2 | 256 |  |  |  |  | Email |
| end_date | TIMESTAMP |  |  |  |  |  | End date |
| entity_id | NUMBER |  | 39 | 0 |  |  | Entity ID |
| entity_tax_reg_num | VARCHAR2 | 30 |  |  |  |  | Entity's tax registration number |
| exchange_rate | NUMBER |  | 30 | 15 |  |  | Exchange rate |
| expected_close | TIMESTAMP |  |  |  |  |  | Expected close |
| external_ref_number | VARCHAR2 | 138 |  |  |  |  | External reference number |
| fax | VARCHAR2 | 100 |  |  |  |  | Fax |
| fob | VARCHAR2 | 13 |  |  |  |  | FOB |
| forecast_type | VARCHAR2 | 384 |  |  |  |  | Forecast type |
| include_in_forecast | VARCHAR2 | 3 |  |  |  |  | Include in forecast |
| incoterm | VARCHAR2 | 100 |  |  |  |  | International commercial term (Incoterm) |
| intercompany_transaction_id | NUMBER |  | 39 | 0 |  |  | Intercompany transaction ID |
| is_actualprodenddate_manual | VARCHAR2 | 3 |  |  |  |  | Whether the actual production end date needs to be entered manually. |
| is_actualprodstartdate_manual | VARCHAR2 | 3 |  |  |  |  | Whether the actual production start date needs to be entered manually. |
| is_advanced_intercompany | VARCHAR2 | 3 |  |  |  |  | Indicates whether the transaction is an advanced intercompany journal entry |
| is_autocalculate_lag | VARCHAR2 | 3 |  |  |  |  | Whether lag times for operation tasks should be calculated. |
| is_compliant | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is compliant |
| is_created_from_merge | VARCHAR2 | 3 |  |  |  |  | Whether the transaction was created from a merge |
| is_cross_sub_transactions | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is a cross-subsidiary transaction |
| is_finance_charge | VARCHAR2 | 3 |  |  |  |  | Is finance charge line |
| is_firmed | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is in the Firmed status |
| is_in_transit_payment | VARCHAR2 | 3 |  |  |  |  | Whether the payment is in transit |
| is_intercompany | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is an intercompany transaction |
| is_merged_into_arrangements | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is to be merged into arrangements |
| is_non_posting | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is non-posting |
| is_override_installments | VARCHAR2 | 3 |  |  |  |  | Whether installments have been overridden |
| is_payment_hold | VARCHAR2 | 3 |  |  |  |  | Whether the transaction has a payment hold |
| is_recurring_bill | VARCHAR2 | 3 |  |  |  |  | Whether the bill is recurring |
| is_reversal | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is a reversal |
| is_ship_complete | VARCHAR2 | 3 |  |  |  |  | Is ship complete |
| is_tax_point_date_override | VARCHAR2 | 3 |  |  |  |  | Indicates whether the tax point date was set manually by the user |
| is_tax_reg_override | VARCHAR2 | 3 |  |  |  |  | Whether a tax regulation override is applied |
| is_wip | VARCHAR2 | 1 |  |  |  |  | Is wip |
| item_revision | NUMBER |  | 39 | 0 |  |  | Item revision |
| job_id | NUMBER |  | 39 | 0 |  |  | Name / job ID |
| landed_cost_allocation_method | VARCHAR2 | 8 |  |  |  |  | Cost allocation method (for example: weight, quantity, or value) |
| last_modified_date | TIMESTAMP |  |  |  |  |  | Date last modified (GMT) |
| lead_source_id | NUMBER |  | 39 | 0 |  |  | Lead source ID |
| location_id | NUMBER |  | 39 | 0 |  |  | Location ID |
| memo | VARCHAR2 | 4000 |  |  |  |  | Memo |
| memorized | VARCHAR2 | 3 |  |  |  |  | Memorized |
| message | VARCHAR2 | 999 |  |  |  |  | Message |
| needs_bill | VARCHAR2 | 3 |  |  |  |  | Needs to be billed |
| needs_revenue_commitment | VARCHAR2 | 3 |  |  |  |  | Needs revenue commitment |
| number_of_pricing_tiers | NUMBER |  | 39 | 0 |  |  | Number of pricing tiers |
| opening_balance_transaction | VARCHAR2 | 3 |  |  |  |  | Opening balance transaction |
| ownership_transfer_id | NUMBER |  | 39 | 0 |  |  | Ownership ID |
| packing_list_instructions | VARCHAR2 | 999 |  |  |  |  | Packing list instructions |
| partner_id | NUMBER |  | 39 | 0 |  |  | Partner ID |
| payment_terms_id | NUMBER |  | 39 | 0 |  |  | Payment terms ID |
| pn_ref_num | VARCHAR2 | 100 |  |  |  |  | P/N reference number |
| probability | NUMBER |  | 6 | 2 |  |  | Probability |
| product_label_instructions | VARCHAR2 | 999 |  |  |  |  | Product label instructions |
| projected_total | NUMBER |  | 20 | 2 |  |  | Projected total |
| promotion_code_id | NUMBER |  | 39 | 0 |  |  | Promotion code ID |
| promotion_code_instance_id | NUMBER |  | 39 | 0 |  |  | Promotion code insurance ID |
| purchase_order_instructions | VARCHAR2 | 999 |  |  |  |  | Purchase order instructions |
| related_tranid | VARCHAR2 | 138 |  |  |  |  | Related transaction ID |
| renewal | TIMESTAMP |  |  |  |  |  | Renewal date |
| revenue_commitment_status | VARCHAR2 | 480 |  |  |  |  | Revenue committed status |
| revenue_committed | TIMESTAMP |  |  |  |  |  | Revenue committed |
| revenue_status | VARCHAR2 | 480 |  |  |  |  | Revenue Status |
| reversing_transaction_id | NUMBER |  | 39 | 0 |  |  | Reversing transaction ID |
| sales_channel_id | NUMBER |  | 39 | 0 | sales_channel_id | Sales_channels | Sales channel ID |
| sales_effective_date | TIMESTAMP |  |  |  |  |  | Sales effective date (for commissions) |
| sales_rep_id | NUMBER |  | 39 | 0 |  |  | Sales rep ID |
| scheduling_method_id | VARCHAR2 | 15 |  |  |  |  | Scheduling method ID |
| shipaddress | VARCHAR2 | 999 |  |  |  |  | Shipping address |
| shipment_received | TIMESTAMP |  |  |  |  |  | Shipment received |
| shipping_item_id | NUMBER |  | 39 | 0 |  |  | Shipping item ID |
| start_date | TIMESTAMP |  |  |  |  |  | Start date |
| status | VARCHAR2 | 4000 |  |  |  |  | Status |
| tax_reg_id | NUMBER |  | 39 | 0 |  |  | Tax regulation ID (no longer supported) |
| title | VARCHAR2 | 200 |  |  |  |  | Title |
| trandate | TIMESTAMP |  |  |  |  |  | Transaction date |
| tranid | VARCHAR2 | 138 |  |  |  |  | Check or document # |
| trans_is_vsoe_bundle | VARCHAR2 | 3 |  |  |  |  | Transaction is VSOE bundle |
| transaction_extid | VARCHAR2 | 255 |  |  |  |  | Transaction external ID |
| transaction_id | NUMBER |  | 39 | 0 |  |  | Internal transaction ID |
| transaction_number | VARCHAR2 | 138 |  |  |  |  | Transaction number |
| transaction_partner | VARCHAR2 | 40 |  |  |  |  | Transaction partner |
| transaction_source | VARCHAR2 | 4000 |  |  |  |  | Source of transaction (name of web site if source is web store) |
| transaction_type | VARCHAR2 | 192 |  |  |  |  | Transaction type |
| transaction_website | NUMBER |  | 39 | 0 |  |  | Numerical ID of source web site |
| transfer_location | NUMBER |  | 39 | 0 |  |  | Transfer location |
| use_item_cost_as_transfer_cost | VARCHAR2 | 3 |  |  |  |  | Whether the Use Item Cost as Transfer Cost preference applies to the transaction |
| visible_in_customer_center | VARCHAR2 | 1 |  |  |  |  | Visible in the Customer Center |
| weighted_total | NUMBER |  | 39 | 0 |  |  | Weighted total |

## Primary key

| PK Column Name |
| --- |
| transaction_id |

## Foreign keys in this table

| FK Name | FK Column Name | PK Table Name | PK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| transactions_accounts_fk | acct_corp_card_expenses_id | Accounts | account_id | 1 |
| transactions_sales_channels_fk | sales_channel_id | Sales_channels | sales_channel_id | 1 |

## Foreign keys referencing this table

| FK Name | PK Column Name | FK Table Name | FK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| Amortization_sched_lines_transactions_fk | transaction_id | Amortization_sched_lines | journal_id | 1 |
| Billing_subscription_lines_transactions_fk | transaction_id | Billing_subscription_lines | purchase_order_id | 1 |
| Billing_subscription_lines_transactions_fk_2 | transaction_id | Billing_subscription_lines | sales_order_id | 1 |
| Billing_subscriptions_transactions_fk | transaction_id | Billing_subscriptions | sales_order_id | 1 |
| Campaignresponsehistory_transactions_fk | transaction_id | Campaignresponsehistory | transaction_id | 1 |
| Employee_time_transactions_fk | transaction_id | Employee_time | transaction_id | 1 |
| Expense_plan_lines_transactions_fk | transaction_id | Expense_plan_lines | journal_id | 1 |
| Expense_plans_transactions_fk | transaction_id | Expense_plans | related_revenue_arrangement_id | 1 |
| Expense_reports_transactions_fk | transaction_id | Expense_reports | expense_report_id | 1 |
| Notes_user_transactions_fk | transaction_id | Notes_user | transaction_id | 1 |
| Opportunities_transactions_fk | transaction_id | Opportunities | reversing_transaction_id | 1 |
| Revenue_plan_lines_transactions_fk | transaction_id | Revenue_plan_lines | journal_id | 1 |
| Revenue_plan_version_lines_transactions_fk | transaction_id | Revenue_plan_version_lines | journal_id | 1 |
| Revrecschedulelines_transactions_fk | transaction_id | Revrecschedulelines | journal_id | 1 |
| System_notes_custom_transactions_fk | transaction_id | System_notes_custom | transaction_id | 1 |
| System_notes_transactions_fk | transaction_id | System_notes | transaction_id | 1 |
| Transaction_address_transactions_fk | transaction_id | Transaction_address | transaction_id | 1 |
| Transaction_book_map_transactions_fk | transaction_id | Transaction_book_map | transaction_id | 1 |
| Transaction_history_transactions_fk | transaction_id | Transaction_history | transaction_id | 1 |
| Transaction_lines_transactions_fk | transaction_id | Transaction_lines | transaction_id | 1 |
| Transaction_links_applied_transactions_fk | transaction_id | Transaction_links | applied_transaction_id | 1 |
| Transaction_links_original_transactions_fk | transaction_id | Transaction_links | original_transaction_id | 1 |
| Transaction_shipping_groups_transactions_fk | transaction_id | Transaction_shipping_groups | transaction_id | 1 |

## This table is included in the following domains

| Domains |
| --- |
| Campaignevents |
| Expense_amortization |
| General_accounting |
| Invoice_with_amortization |
| Multibooks |
| Revenue_recognition |

## Domain diagrams

- Campaignevents: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/campaignevents.png
- Expense_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/expense_amortization.png
- General_accounting: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/general_accounting.png
- Invoice_with_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/invoice_with_amortization.png
- Multibooks: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/multibooks.png
- Revenue_recognition: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/revenue_recognition.png

Generated on 2024-11-25 for version 2024.2

Other table names (as listed by the browser):

Task_contacts
Tasks
Tax_items
Territory
Time_based_charge_rules
Timesheet
Topic
Trans_partner_sales_teams
Transaction_address
Transaction_bin_numbers
Transaction_book_map
Transaction_cost_components
Transaction_history
Transaction_inventory_numbers
Transaction_line_book_map
Transaction_lines
Transaction_links
Transaction_sales_teams
Transaction_shipping_groups
Transaction_tax_detail
Transaction_tracking_numbers
Transactions

---

# Transaction_lines (canonical: transactionLine)

This section documents the **Transaction_lines** table for SuiteAnalytics Connect (JDBC).

## Browsers and Reference Links

- Schema Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html#schematab
- Records Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html#scripttab
- Connect Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html#browsertab
- Analytics Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html#analyticstab

Additional navigation links:
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/schema/index.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/script/index.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html
- https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/analytics/index.html

## Transaction_lines Table – Key Notes

- The **Transaction Column Fields** custom field is available for the **Transaction Lines** table.
- **Credit and debit amounts are NOT exposed** as columns in **Transaction Lines**. Use this table to obtain credit/debit amounts for transactions.
- **Tax line unique key updates** only in these scenarios:
  - Tax type changes on a transaction line where that tax type is used on only one line.
  - A transaction line is added with a different tax type than existing lines.
  - A line (or all lines sharing the same tax type) is removed and re-added with a different tax type. If only some lines sharing the same tax type are removed, the existing unique key is re-assigned when re-added.
- **Landed cost category names** can be obtained by including `memo` in queries of **TRANSACTION_LINES**. For lines where `is_landed_cost = 'T'`, `memo` is written as `<Landed Cost Category Name>:<Item Name>`.

Related links:
- Linking Gift Certificates to Transaction Line Items: https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_4400768017
- Connect Access to Transaction Credit and Debit Amounts: https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_4400769955

## Transaction_lines – Columns

| Name | Type | Length | Precision | Scale | References | In | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| account_id | NUMBER |  | 39 | 0 | account_id | Accounts | Account ID |
| alt_sales_amount | NUMBER |  | 20 | 2 |  |  | Alt sales amount |
| amortization_residual | VARCHAR2 | 42 |  |  |  |  | Amortization residual |
| amount | NUMBER |  | 20 | 2 |  |  | Amount |
| amount_foreign | NUMBER |  | 20 | 2 |  |  | Foreign currency amount |
| amount_foreign_linked | NUMBER |  | 30 | 15 |  |  | Foreign currency amount linked |
| amount_linked | NUMBER |  | 20 | 2 |  |  | Amount linked |
| amount_pending | NUMBER |  | 20 | 2 |  |  | Amount pending |
| amount_settlement | NUMBER |  | 20 | 2 |  |  | Amount settlement |
| amount_taxable | NUMBER |  | 20 | 2 |  |  | Amount taxable |
| amount_taxed | NUMBER |  | 20 | 2 |  |  | Amount taxed |
| bill_variance_status | VARCHAR2 | 128 |  |  |  |  | Bill variance status |
| billing_schedule_id | NUMBER |  | 39 | 0 | billing_schedule_id | Billing_schedule_descriptions | Billing schedule ID |
| billing_subsidiary_id | NUMBER |  | 39 | 0 |  |  | Billing subsidiary ID |
| bom_quantity | NUMBER |  | 18 | 8 |  |  | Bom quantity |
| catch_up_period_id | NUMBER |  | 39 | 0 |  |  | Catch-up period ID |
| charge_rule_id | NUMBER |  | 39 | 0 |  |  | Charge rule ID |
| charge_type | NUMBER |  | 39 | 0 |  |  | Charge type |
| class_id | NUMBER |  | 39 | 0 |  |  | Class ID |
| company_id | NUMBER |  | 39 | 0 |  |  | Company ID |
| component_id | NUMBER |  | 39 | 0 |  |  | Component ID |
| component_yield | NUMBER |  | 39 | 0 |  |  | Component yield |
| cost_estimate_type | VARCHAR2 | 200 |  |  |  |  | Cost estimate type |
| date_cleared | TIMESTAMP |  |  |  |  |  | Date cleared |
| date_closed | TIMESTAMP |  |  |  |  |  | Date closed |
| date_created | TIMESTAMP |  |  |  |  |  | Date created |
| date_last_modified_gmt | TIMESTAMP |  |  |  |  |  | Date last modified in GMT format |
| date_requested | TIMESTAMP |  |  |  |  |  | Date requested |
| date_revenue_committed | TIMESTAMP |  |  |  |  |  | Date revenue committed |
| delay_rev_rec | VARCHAR2 | 3 |  |  |  |  | Delay revenue recognition |
| department_id | NUMBER |  | 39 | 0 |  |  | Department ID |
| do_not_display_line | VARCHAR2 | 3 |  |  |  |  | Do not display line |
| do_not_print_line | VARCHAR2 | 3 |  |  |  |  | Do not print line |
| do_restock | VARCHAR2 | 3 |  |  |  |  | Do restock |
| estimated_cost | NUMBER |  | 20 | 2 |  |  | Estimated cost |
| estimated_cost_foreign | NUMBER |  | 20 | 2 |  |  | Estimated cost in foreign currency |
| expected_receipt_date | TIMESTAMP |  |  |  |  |  | Expected receipt date |
| expense_category_id | NUMBER |  | 39 | 0 |  |  | Expense category ID |
| gl_number | VARCHAR2 | 80 |  |  |  |  | GL number |
| gl_sequence | VARCHAR2 | 256 |  |  |  |  | GL sequence |
| gl_sequence_id | NUMBER |  | 39 | 0 |  |  | GL sequence ID |
| gross_amount | NUMBER |  | 39 | 0 |  |  | Gross amount |
| has_cost_line | VARCHAR2 | 3 |  |  |  |  | Has cost line |
| is_allocation | VARCHAR2 | 1 |  |  |  |  | Is allocation |
| is_amortization_rev_rec | VARCHAR2 | 3 |  |  |  |  | Is amortization revenue recognition |
| is_commitment_confirmed | VARCHAR2 | 3 |  |  |  |  | Is commitment confirmed |
| is_cost_line | VARCHAR2 | 3 |  |  |  |  | Is cost line |
| is_custom_line | VARCHAR2 | 3 |  |  |  |  | Is custom line |
| is_exclude_from_rate_request | VARCHAR2 | 3 |  |  |  |  | Is excluded from rate request |
| is_fx_variance | VARCHAR2 | 3 |  |  |  |  | Whether is foreign exchange variance |
| is_item_value_adjustment | VARCHAR2 | 3 |  |  |  |  | Is item value adjustment |
| is_landed_cost | VARCHAR2 | 3 |  |  |  |  | Whether line is a landed cost (see memo note) |
| is_scrap | VARCHAR2 | 3 |  |  |  |  | Is scrap |
| is_vsoe_allocation_line | VARCHAR2 | 3 |  |  |  |  | Line is VSOE allocation |
| isbillable | VARCHAR2 | 3 |  |  |  |  | Billable |
| iscleared | VARCHAR2 | 3 |  |  |  |  | Is cleared |
| isnonreimbursable | VARCHAR2 | 3 |  |  |  |  | Is non-reimbursable |
| istaxable | VARCHAR2 | 3 |  |  |  |  | Taxable |
| item_count | NUMBER |  | 18 | 8 |  |  | Item count |
| item_id | NUMBER |  | 39 | 0 |  |  | Item ID |
| item_received | VARCHAR2 | 3 |  |  |  |  | Item received |
| item_source | VARCHAR2 | 30 |  |  |  |  | Item source |
| item_unit_price | VARCHAR2 | 42 |  |  |  |  | Item unit price |
| kit_part_number | NUMBER |  | 39 | 0 |  |  | Kit name/number |
| landed_cost_source_line_id | NUMBER |  | 38 | 0 |  |  | transaction_line_id for the transaction to which this landed cost line is attached |
| location_id | NUMBER |  | 39 | 0 |  |  | Location ID |
| match_bill_to_receipt | VARCHAR2 | 1 |  |  |  |  | Match bill to receipt |
| memo | VARCHAR2 | 4000 |  |  |  |  | Memo |
| needs_revenue_element | VARCHAR2 | 3 |  |  |  |  | Needs revenue element |
| net_amount | NUMBER |  | 39 | 0 |  |  | Net amount |
| net_amount_foreign | NUMBER |  | 39 | 0 |  |  | Net amount in foreign currency |
| non_posting_line | VARCHAR2 | 3 |  |  |  |  | Non posting line |
| number_billed | NUMBER |  | 18 | 8 |  |  | Number billed |
| operation_sequence_number | NUMBER |  | 39 | 0 |  |  | Operation sequence number |
| order_allocation_strategy_id | NUMBER |  | 39 | 0 | order_allocation_strategy_id | Order_allocation_strategies | Order allocation strategy ID |
| order_priority | NUMBER |  | 20 | 2 |  |  | Order priority |
| payment_method_id | NUMBER |  | 39 | 0 |  |  | Payment method ID |
| payroll_item_id | NUMBER |  | 39 | 0 |  |  | Payroll item ID |
| payroll_wage_base_amount | NUMBER |  | 20 | 2 |  |  | Payroll wage base amount |
| payroll_year_to_date_amount | NUMBER |  | 20 | 2 |  |  | Payroll YTD amount |
| period_closed | TIMESTAMP |  |  |  |  |  | Period closed |
| price_type_id | NUMBER |  | 39 | 0 |  |  | Price type ID |
| project_task_id | NUMBER |  | 39 | 0 |  |  | Project task ID |
| purchase_contract_id | NUMBER |  | 39 | 0 |  |  | Purchase contract ID |
| quantity_allocated | NUMBER |  | 30 | 15 |  |  | Quantity allocated |
| quantity_committed | NUMBER |  | 30 | 15 |  |  | Quantity committed |
| quantity_packed | NUMBER |  | 18 | 8 |  |  | Quantity packed |
| quantity_picked | NUMBER |  | 18 | 8 |  |  | Quantity picked |
| quantity_received_in_shipment | NUMBER |  | 18 | 8 |  |  | Quantity received in shipment |
| receivebydate | TIMESTAMP |  |  |  |  |  | Receive by date |
| reimbursement_type | VARCHAR2 | 128 |  |  |  |  | Reimbursement type |
| related_company_id | NUMBER |  | 39 | 0 |  |  | Related company ID |
| rev_rec_end_date | TIMESTAMP |  |  |  |  |  | Revenue recognition end date |
| rev_rec_rule_id | NUMBER |  | 39 | 0 |  |  | Revenue recognition rule ID |
| rev_rec_start_date | TIMESTAMP |  |  |  |  |  | Revenue recognition start date |
| revenue_element_id | NUMBER |  | 39 | 0 |  |  | Revenue element ID |
| schedule_id | NUMBER |  | 39 | 0 |  |  | Revenue recognition schedule ID or amortization schedule ID |
| shipdate | TIMESTAMP |  |  |  |  |  | Ship date |
| shipment_received | TIMESTAMP |  |  |  |  |  | Shipment received |
| shipping_group_id | NUMBER |  | 39 | 0 | shipping_group_id | Transaction_shipping_groups | Shipping group ID |
| source_subsidiary_id | NUMBER |  | 39 | 0 | subsidiary_id | Subsidiaries | Source subsidiary ID |
| subscription_line_id | NUMBER |  | 39 | 0 |  |  | Subscription line ID |
| subsidiary_id | NUMBER |  | 39 | 0 | subsidiary_id | Subsidiaries | Subsidiary ID |
| tax_item_id | NUMBER |  | 39 | 0 |  |  | Tax item ID |
| tax_type | VARCHAR2 | 64 |  |  |  |  | Tax type |
| term_in_months | NUMBER |  | 39 | 0 |  |  | Term in months |
| tobeemailed | VARCHAR2 | 3 |  |  |  |  | To be emailed |
| tobefaxed | VARCHAR2 | 3 |  |  |  |  | To be faxed |
| tobeprinted | VARCHAR2 | 3 |  |  |  |  | To be printed |
| transaction_discount_line | VARCHAR2 | 3 |  |  |  |  | Transaction discount line |
| transaction_id | NUMBER |  | 39 | 0 | transaction_id | Transaction_shipping_groups; Transactions | Transaction ID |
| transaction_line_id | NUMBER |  | 39 | 0 |  |  | Transaction line ID |
| transaction_order | NUMBER |  | 39 | 0 |  |  | Transaction order |
| transfer_order_item_line | NUMBER |  | 39 | 0 |  |  | Transfer order item line |
| transfer_order_line_type | VARCHAR2 | 25 |  |  |  |  | Transfer order line type |
| unique_key | NUMBER |  | 39 | 0 |  |  | Unique key |
| unit_cost_override | NUMBER |  | 30 | 15 |  |  | Unit cost override |
| unit_of_measure_id | NUMBER |  | 39 | 0 |  |  | Unit of measure ID |
| vsoe_allocation | NUMBER |  | 20 | 2 |  |  | VSOE allocation |
| vsoe_amt | NUMBER |  | 20 | 2 |  |  | VSOE amount |
| vsoe_deferral | VARCHAR2 | 28 |  |  |  |  | VSOE deferral |
| vsoe_delivered | VARCHAR2 | 3 |  |  |  |  | VSOE delivered |
| vsoe_discount | VARCHAR2 | 12 |  |  |  |  | VSOE discount |
| vsoe_price | NUMBER |  | 30 | 15 |  |  | VSOE price |

## Primary key (Composite)

| PK Column Name |
| --- |
| transaction_id |
| transaction_line_id |

## Foreign keys in this table

| FK Name | FK Column Name | PK Table Name | PK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| transaction_lines_accounts_fk | account_id | Accounts | account_id | 1 |
| transaction_lines_billing_schedule_descriptions_fk | billing_schedule_id | Billing_schedule_descriptions | billing_schedule_id | 1 |
| transaction_lines_order_allocation_strategies_fk | order_allocation_strategy_id | Order_allocation_strategies | order_allocation_strategy_id | 1 |
| transaction_lines_subsidiaries_fk_1 | subsidiary_id | Subsidiaries | subsidiary_id | 1 |
| transaction_lines_subsidiaries_fk_2 | source_subsidiary_id | Subsidiaries | subsidiary_id | 1 |
| transaction_lines_transaction_shipping_groups_fk | transaction_id | Transaction_shipping_groups | transaction_id | 1 |
| transaction_lines_transaction_shipping_groups_fk | shipping_group_id | Transaction_shipping_groups | shipping_group_id | 2 |
| transaction_lines_transactions_fk | transaction_id | Transactions | transaction_id | 1 |

## Foreign keys referencing this table

| FK Name | PK Column Name | FK Table Name | FK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| Employee_time_transaction_lines_fk | transaction_id | Employee_time | transaction_id | 1 |
| Employee_time_transaction_lines_fk | transaction_line_id | Employee_time | transaction_line_id | 2 |
| Expense_plans_transaction_lines_fk | transaction_id | Expense_plans | transaction_doc_id | 1 |
| Expense_plans_transaction_lines_fk_1 | transaction_line_id | Expense_plans | transaction_line_id | 1 |
| System_notes_custom_transaction_lines_fk | transaction_id | System_notes_custom | line_transaction_id | 1 |
| System_notes_custom_transaction_lines_fk | transaction_line_id | System_notes_custom | line_id | 2 |
| System_notes_transaction_lines_fk | transaction_id | System_notes | line_transaction_id | 1 |
| System_notes_transaction_lines_fk | transaction_line_id | System_notes | line_id | 2 |
| Transaction_line_book_map_transaction_lines_fk | transaction_id | Transaction_line_book_map | transaction_id | 1 |
| Transaction_line_book_map_transaction_lines_fk | transaction_line_id | Transaction_line_book_map | transaction_line_id | 2 |
| Transaction_links_applied_transaction_lines_fk | transaction_id | Transaction_links | applied_transaction_id | 1 |
| Transaction_links_applied_transaction_lines_fk | transaction_line_id | Transaction_links | applied_transaction_line_id | 2 |
| Transaction_links_original_transaction_lines_fk | transaction_id | Transaction_links | original_transaction_id | 1 |
| Transaction_links_original_transaction_lines_fk | transaction_line_id | Transaction_links | original_transaction_line_id | 2 |
| Transaction_tax_detail_transaction_lines_fk | transaction_id | Transaction_tax_detail | transaction_id | 1 |
| Transaction_tax_detail_transaction_lines_fk | transaction_line_id | Transaction_tax_detail | transaction_line_id | 2 |

## This table is included in the following domains

| Domains |
| --- |
| Expense_amortization |
| General_accounting |
| Invoice_with_amortization |
| Multibooks |
| Revenue_recognition |

## Domain diagrams

- Expense_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/expense_amortization.png
- General_accounting: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/general_accounting.png
- Invoice_with_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/invoice_with_amortization.png
- Multibooks: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/multibooks.png
- Revenue_recognition: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/revenue_recognition.png

Generated on 2024-11-25 for version 2024.2
</attachment>
</attachments>
<context>
The current date is February 1, 2026.
Terminals:
Terminal: zsh
Last Command: git push
Cwd: /Users/johnramonelroque/Documents/GitHub/jrq-netsuite-ai
Exit Code: 0
Terminal: zsh
Last Command: source /Users/johnramonelroque/Documents/GitHub/jrq-netsuite-ai/.venv/bin/activate
Cwd: /Users/johnramonelroque/Documents/GitHub/jrq-netsuite-ai
Exit Code: 0
Terminal: zsh
Last Command: git add -A && git commit -m "Improve dashboard iframe sizing and scrolling" && git push
Cwd: /Users/johnramonelroque/Documents/GitHub/jrq-netsuite-ai
Exit Code: 0

</context>
<editorContext>
The user's current file is /Users/johnramonelroque/Documents/GitHub/jrq-netsuite-ai/netsuite-ai-webapp/backend/app/web/index.html. The current selection is from line 489 to line 489.
</editorContext>
<reminderInstructions>
You are an agent - you must keep going until the user's query is completely resolved, before ending your turn and yielding back to the user. ONLY terminate your turn when you are sure that the problem is solved, or you absolutely cannot continue.
You take action when possible- the user is expecting YOU to take action and go to work for them. Don't ask unnecessary questions about the details if you can simply DO something useful instead.

</reminderInstructions>
<userRequest>
yes do that, this is the content, make it understandable by the LLM 

- [Schema Browser](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#schematab)
- [Records Browser](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#scripttab)
- [Connect Browser](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#browsertab)
- [Analytics Browser](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html#analyticstab)

[go to link](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/schema/index.html)

[go to link](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/script/record/transaction.html)

[go to link](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction.html)

[go to link](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/analytics/index.html)

Select a table alphabetically:

ABCDEFGIJLMNOPQRSTUVW

or select a domain:

Select package...CampaigneventsCampaignsExpense\_amortizationGeneral\_accountingInvoice\_with\_amortizationMultibooksRevenue\_recognition▽

Task\_contacts

Tasks

Tax\_items

Territory

Time\_based\_charge\_rules

Timesheet

Topic

Trans\_partner\_sales\_teams

Transaction\_address

Transaction\_bin\_numbers

Transaction\_book\_map

Transaction\_cost\_components

Transaction\_history

Transaction\_inventory\_numbers

Transaction\_line\_book\_map

Transaction\_lines

Transaction\_links

Transaction\_sales\_teams

Transaction\_shipping\_groups

Transaction\_tax\_detail

Transaction\_tracking\_numbers

Transactions

# Transactions (canonical: transaction)


The Transaction Body Fields custom field is available for the Transactions table.

**Important:** Credit and debit amounts are not exposed as columns in the Transactions table. However, you can query the Transaction Lines table to obtain transaction credit and debit amounts. For more details, see [Connect Access to Transaction Credit and Debit Amounts](https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_4400769955).

**Important:** Item count and quantity values are not exposed as columns in the Transactions table. However, you can query the Transaction Lines table to obtain these values. For more details, see [Connect Access to Transaction Quantities](https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_1512507697).

## Columns

| Name | Type | Length | Precision | Scale | References | In | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| account\_based\_number | VARCHAR2 | 138 |  |  |  |  | Account based number |
| accounting\_book\_id | NUMBER |  | 39 | 0 |  |  | Accounting book ID |
| accounting\_period\_id | NUMBER |  | 39 | 0 |  |  | Accounting period ID |
| acct\_corp\_card\_expenses\_id | NUMBER |  | 39 | 0 | account\_id | [Accounts](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html?mode= "record__account") | ID of the account for corporate card in expense report |
| amount\_unbilled | NUMBER |  | 20 | 2 |  |  | Amount unbilled |
| bill\_pay\_transaction | VARCHAR2 | 3 |  |  |  |  | Bill pay transaction |
| billaddress | VARCHAR2 | 999 |  |  |  |  | Billing address |
| billing\_account\_id | NUMBER |  | 39 | 0 |  |  | Billing account ID |
| billing\_instructions | VARCHAR2 | 999 |  |  |  |  | Billing instructions |
| buildable | NUMBER |  | 39 | 0 |  |  | The number of assemblies that can be built with the current supplies. |
| bulk\_submission\_id | NUMBER |  | 39 | 0 |  |  | Bulk submission ID |
| carrier | VARCHAR2 | 100 |  |  |  |  | Carrier |
| closed | TIMESTAMP |  |  |  |  |  | Closed |
| company\_status\_id | NUMBER |  | 39 | 0 |  |  | Company status ID |
| contract\_cost\_amount | NUMBER |  | 20 | 2 |  |  | Contract cost amount |
| contract\_defer\_expense\_acct\_id | NUMBER |  | 39 | 0 |  |  | Contract defer expense account ID |
| contract\_expense\_acct\_id | NUMBER |  | 39 | 0 |  |  | Contract expense account ID |
| contract\_expense\_src\_acct\_id | NUMBER |  | 39 | 0 |  |  | Contract acquisition expense source account |
| create\_date | TIMESTAMP |  |  |  |  |  | Creation date (GMT) |
| created\_by\_id | NUMBER |  | 39 | 0 |  |  | ID of the creator |
| created\_from\_id | NUMBER |  | 39 | 0 |  |  | Created from ID |
| currency\_id | NUMBER |  | 39 | 0 |  |  | Currency ID |
| custom\_form\_id | NUMBER |  | 39 | 0 |  |  | Custom form ID |
| date\_actual\_prod\_end | TIMESTAMP |  |  |  |  |  | The date production ends. |
| date\_actual\_prod\_start | TIMESTAMP |  |  |  |  |  | The date production starts. |
| date\_as\_of | TIMESTAMP |  |  |  |  |  | As of date |
| date\_bid\_close | TIMESTAMP |  |  |  |  |  | Bid close date |
| date\_bid\_open | TIMESTAMP |  |  |  |  |  | Bid open date |
| date\_contract\_cost\_accrual | TIMESTAMP |  |  |  |  |  | Date contract cost accrual |
| date\_last\_modified | TIMESTAMP |  |  |  |  |  | Date last modified (GMT) |
| date\_tax\_point | TIMESTAMP |  |  |  |  |  | Transaction date determining taxability rules |
| due\_date | TIMESTAMP |  |  |  |  |  | Due date |
| email | VARCHAR2 | 256 |  |  |  |  | Email |
| end\_date | TIMESTAMP |  |  |  |  |  | End date |
| entity\_id | NUMBER |  | 39 | 0 |  |  | Entity ID |
| entity\_tax\_reg\_num | VARCHAR2 | 30 |  |  |  |  | Entity's tax registration number |
| exchange\_rate | NUMBER |  | 30 | 15 |  |  | Exchange rate |
| expected\_close | TIMESTAMP |  |  |  |  |  | Expected close |
| external\_ref\_number | VARCHAR2 | 138 |  |  |  |  | External reference number |
| fax | VARCHAR2 | 100 |  |  |  |  | Fax |
| fob | VARCHAR2 | 13 |  |  |  |  | FOB |
| forecast\_type | VARCHAR2 | 384 |  |  |  |  | Forecast type |
| include\_in\_forecast | VARCHAR2 | 3 |  |  |  |  | Include in forecast |
| incoterm | VARCHAR2 | 100 |  |  |  |  | International commercial term (Incoterm) |
| intercompany\_transaction\_id | NUMBER |  | 39 | 0 |  |  | Intercompany transaction ID |
| is\_actualprodenddate\_manual | VARCHAR2 | 3 |  |  |  |  | Whether the actual production end date needs to be entered manually. |
| is\_actualprodstartdate\_manual | VARCHAR2 | 3 |  |  |  |  | Whether the actual production start date needs to be entered manually. |
| is\_advanced\_intercompany | VARCHAR2 | 3 |  |  |  |  | Indicates whether the transaction is an advanced intercompany journal entry |
| is\_autocalculate\_lag | VARCHAR2 | 3 |  |  |  |  | Whether lag times for operation tasks should be calculated. |
| is\_compliant | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is compliant |
| is\_created\_from\_merge | VARCHAR2 | 3 |  |  |  |  | Whether the transaction was created from a merge |
| is\_cross\_sub\_transactions | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is a cross-subsidiary transaction |
| is\_finance\_charge | VARCHAR2 | 3 |  |  |  |  | Is finance charge line |
| is\_firmed | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is in the Firmed status |
| is\_in\_transit\_payment | VARCHAR2 | 3 |  |  |  |  | Whether the payment is in transit |
| is\_intercompany | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is an intercompany transaction |
| is\_merged\_into\_arrangements | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is to be merged into arrangements |
| is\_non\_posting | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is non-posting |
| is\_override\_installments | VARCHAR2 | 3 |  |  |  |  | Whether installments have been overridden |
| is\_payment\_hold | VARCHAR2 | 3 |  |  |  |  | Whether the transaction has a payment hold |
| is\_recurring\_bill | VARCHAR2 | 3 |  |  |  |  | Whether the bill is recurring |
| is\_reversal | VARCHAR2 | 3 |  |  |  |  | Whether the transaction is a reversal |
| is\_ship\_complete | VARCHAR2 | 3 |  |  |  |  | Is ship complete |
| is\_tax\_point\_date\_override | VARCHAR2 | 3 |  |  |  |  | Indicates whether the tax point date was set manually by the user |
| is\_tax\_reg\_override | VARCHAR2 | 3 |  |  |  |  | Whether a tax regulation override is applied |
| is\_wip | VARCHAR2 | 1 |  |  |  |  | Is wip |
| item\_revision | NUMBER |  | 39 | 0 |  |  | Item revision |
| job\_id | NUMBER |  | 39 | 0 |  |  | Name / job ID |
| landed\_cost\_allocation\_method | VARCHAR2 | 8 |  |  |  |  | Cost allocation method (for example: weight, quantity, or value) |
| last\_modified\_date | TIMESTAMP |  |  |  |  |  | Date last modified (GMT) |
| lead\_source\_id | NUMBER |  | 39 | 0 |  |  | Lead source ID |
| location\_id | NUMBER |  | 39 | 0 |  |  | Location ID |
| memo | VARCHAR2 | 4000 |  |  |  |  | Memo |
| memorized | VARCHAR2 | 3 |  |  |  |  | Memorized |
| message | VARCHAR2 | 999 |  |  |  |  | Message |
| needs\_bill | VARCHAR2 | 3 |  |  |  |  | Needs to be billed |
| needs\_revenue\_commitment | VARCHAR2 | 3 |  |  |  |  | Needs revenue commitment |
| number\_of\_pricing\_tiers | NUMBER |  | 39 | 0 |  |  | Number of pricing tiers |
| opening\_balance\_transaction | VARCHAR2 | 3 |  |  |  |  | Opening balance transaction |
| ownership\_transfer\_id | NUMBER |  | 39 | 0 |  |  | Ownership ID |
| packing\_list\_instructions | VARCHAR2 | 999 |  |  |  |  | Packing list instructions |
| partner\_id | NUMBER |  | 39 | 0 |  |  | Partner ID |
| payment\_terms\_id | NUMBER |  | 39 | 0 |  |  | Payment terms ID |
| pn\_ref\_num | VARCHAR2 | 100 |  |  |  |  | P/N reference number |
| probability | NUMBER |  | 6 | 2 |  |  | Probability |
| product\_label\_instructions | VARCHAR2 | 999 |  |  |  |  | Product label instructions |
| projected\_total | NUMBER |  | 20 | 2 |  |  | Projected total |
| promotion\_code\_id | NUMBER |  | 39 | 0 |  |  | Promotion code ID |
| promotion\_code\_instance\_id | NUMBER |  | 39 | 0 |  |  | Promotion code insurance ID |
| purchase\_order\_instructions | VARCHAR2 | 999 |  |  |  |  | Purchase order instructions |
| related\_tranid | VARCHAR2 | 138 |  |  |  |  | Related transaction ID |
| renewal | TIMESTAMP |  |  |  |  |  | Renewal date |
| revenue\_commitment\_status | VARCHAR2 | 480 |  |  |  |  | Revenue committed status |
| revenue\_committed | TIMESTAMP |  |  |  |  |  | Revenue committed |
| revenue\_status | VARCHAR2 | 480 |  |  |  |  | Revenue Status |
| reversing\_transaction\_id | NUMBER |  | 39 | 0 |  |  | Reversing transaction ID |
| sales\_channel\_id | NUMBER |  | 39 | 0 | sales\_channel\_id | [Sales\_channels](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/saleschannel.html?mode= "record__saleschannel") | Sales channel ID |
| sales\_effective\_date | TIMESTAMP |  |  |  |  |  | Sales effective date (for commissions) |
| sales\_rep\_id | NUMBER |  | 39 | 0 |  |  | Sales rep ID |
| scheduling\_method\_id | VARCHAR2 | 15 |  |  |  |  | Scheduling method ID |
| shipaddress | VARCHAR2 | 999 |  |  |  |  | Shipping address |
| shipment\_received | TIMESTAMP |  |  |  |  |  | Shipment received |
| shipping\_item\_id | NUMBER |  | 39 | 0 |  |  | Shipping item ID |
| start\_date | TIMESTAMP |  |  |  |  |  | Start date |
| status | VARCHAR2 | 4000 |  |  |  |  | Status |
| tax\_reg\_id | NUMBER |  | 39 | 0 |  |  | Tax regulation ID (no longer supported) |
| title | VARCHAR2 | 200 |  |  |  |  | Title |
| trandate | TIMESTAMP |  |  |  |  |  | Transaction date |
| tranid | VARCHAR2 | 138 |  |  |  |  | Check or document # |
| trans\_is\_vsoe\_bundle | VARCHAR2 | 3 |  |  |  |  | Transaction is VSOE bundle |
| transaction\_extid | VARCHAR2 | 255 |  |  |  |  | Transaction external ID |
| transaction\_id | NUMBER |  | 39 | 0 |  |  | Internal transaction ID |
| transaction\_number | VARCHAR2 | 138 |  |  |  |  | Transaction number |
| transaction\_partner | VARCHAR2 | 40 |  |  |  |  | Transaction partner |
| transaction\_source | VARCHAR2 | 4000 |  |  |  |  | Source of transaction (name of web site if source is web store) |
| transaction\_type | VARCHAR2 | 192 |  |  |  |  | Transaction type |
| transaction\_website | NUMBER |  | 39 | 0 |  |  | Numerical ID of source web site |
| transfer\_location | NUMBER |  | 39 | 0 |  |  | Transfer location |
| use\_item\_cost\_as\_transfer\_cost | VARCHAR2 | 3 |  |  |  |  | Whether the Use Item Cost as Transfer Cost preference applies to the transaction |
| visible\_in\_customer\_center | VARCHAR2 | 1 |  |  |  |  | Visible in the Customer Center |
| weighted\_total | NUMBER |  | 39 | 0 |  |  | Weighted total |

## Primary key

| PK Column Name |
| --- |
| transaction\_id |

## Foreign keys in this table

| FK Name | FK Column Name | PK Table Name | PK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| transactions\_accounts\_fk | acct\_corp\_card\_expenses\_id | [Accounts](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html?mode= "record__account") | account\_id | 1 |
| transactions\_sales\_channels\_fk | sales\_channel\_id | [Sales\_channels](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/saleschannel.html?mode= "record__saleschannel") | sales\_channel\_id | 1 |

## Foreign keys referencing this table

| FK Name | PK Column Name | FK Table Name | FK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| Amortization\_sched\_lines\_transactions\_fk | transaction\_id | [Amortization\_sched\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/amortization_sched_lines.html?mode= "record__amortization_sched_lines") | journal\_id | 1 |
| Billing\_subscription\_lines\_transactions\_fk | transaction\_id | [Billing\_subscription\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/billing_subscription_lines.html?mode= "record__billing_subscription_lines") | purchase\_order\_id | 1 |
| Billing\_subscription\_lines\_transactions\_fk\_2 | transaction\_id | [Billing\_subscription\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/billing_subscription_lines.html?mode= "record__billing_subscription_lines") | sales\_order\_id | 1 |
| Billing\_subscriptions\_transactions\_fk | transaction\_id | [Billing\_subscriptions](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/billing_subscriptions.html?mode= "record__billing_subscriptions") | sales\_order\_id | 1 |
| Campaignresponsehistory\_transactions\_fk | transaction\_id | [Campaignresponsehistory](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/campaignresponsehistory.html?mode= "record__campaignresponsehistory") | transaction\_id | 1 |
| Employee\_time\_transactions\_fk | transaction\_id | [Employee\_time](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/employee_time.html?mode= "record__employee_time") | transaction\_id | 1 |
| Expense\_plan\_lines\_transactions\_fk | transaction\_id | [Expense\_plan\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/expense_plan_lines.html?mode= "record__expense_plan_lines") | journal\_id | 1 |
| Expense\_plans\_transactions\_fk | transaction\_id | [Expense\_plans](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/expenseplan.html?mode= "record__expenseplan") | related\_revenue\_arrangement\_id | 1 |
| Expense\_reports\_transactions\_fk | transaction\_id | [Expense\_reports](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/expensereport.html?mode= "record__expensereport") | expense\_report\_id | 1 |
| Notes\_user\_transactions\_fk | transaction\_id | [Notes\_user](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/notes_user.html?mode= "record__notes_user") | transaction\_id | 1 |
| Opportunities\_transactions\_fk | transaction\_id | [Opportunities](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/opportunities.html?mode= "record__opportunities") | reversing\_transaction\_id | 1 |
| Revenue\_plan\_lines\_transactions\_fk | transaction\_id | [Revenue\_plan\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/revenue_plan_lines.html?mode= "record__revenue_plan_lines") | journal\_id | 1 |
| Revenue\_plan\_version\_lines\_transactions\_fk | transaction\_id | [Revenue\_plan\_version\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/revenue_plan_version_lines.html?mode= "record__revenue_plan_version_lines") | journal\_id | 1 |
| Revrecschedulelines\_transactions\_fk | transaction\_id | [Revrecschedulelines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/revrecschedulelines.html?mode= "record__revrecschedulelines") | journal\_id | 1 |
| System\_notes\_custom\_transactions\_fk | transaction\_id | [System\_notes\_custom](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/system_notes_custom.html?mode= "record__system_notes_custom") | transaction\_id | 1 |
| System\_notes\_transactions\_fk | transaction\_id | [System\_notes](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/system_notes.html?mode= "record__system_notes") | transaction\_id | 1 |
| Transaction\_address\_transactions\_fk | transaction\_id | [Transaction\_address](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_address.html?mode= "record__transaction_address") | transaction\_id | 1 |
| Transaction\_book\_map\_transactions\_fk | transaction\_id | [Transaction\_book\_map](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_book_map.html?mode= "record__transaction_book_map") | transaction\_id | 1 |
| Transaction\_history\_transactions\_fk | transaction\_id | [Transaction\_history](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_history.html?mode= "record__transaction_history") | transaction\_id | 1 |
| Transaction\_lines\_transactions\_fk | transaction\_id | [Transaction\_lines](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_lines.html?mode= "record__transaction_lines") | transaction\_id | 1 |
| Transaction\_links\_applied\_transactions\_fk | transaction\_id | [Transaction\_links](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_links.html?mode= "record__transaction_links") | applied\_transaction\_id | 1 |
| Transaction\_links\_original\_transactions\_fk | transaction\_id | [Transaction\_links](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_links.html?mode= "record__transaction_links") | original\_transaction\_id | 1 |
| Transaction\_shipping\_groups\_transactions\_fk | transaction\_id | [Transaction\_shipping\_groups](https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/transaction_shipping_groups.html?mode= "record__transaction_shipping_groups") | transaction\_id | 1 |

## This table is included in the following domains

| Domains |
| --- |
| Campaignevents |
| Expense_amortization |
| General_accounting |
| Invoice_with_amortization |
| Multibooks |
| Revenue_recognition |

## Domain diagrams

- Campaignevents: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/campaignevents.png
- Expense_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/expense_amortization.png
- General_accounting: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/general_accounting.png
- Invoice_with_amortization: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/invoice_with_amortization.png
- Multibooks: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/multibooks.png
- Revenue_recognition: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/diagrams/revenue_recognition.png

Generated on 2024-11-25 for version 2024.2

Other table names (as listed by the browser):

Task_contacts
Tasks
Tax_items
Territory
Time_based_charge_rules
Timesheet
Topic
Trans_partner_sales_teams
Transaction_address
Transaction_bin_numbers
Transaction_book_map
Transaction_cost_components
Transaction_history
Transaction_inventory_numbers
Transaction_line_book_map
Transaction_lines
Transaction_links
Transaction_sales_teams
Transaction_shipping_groups
Transaction_tax_detail
Transaction_tracking_numbers
Transactions

---

# Accounts (canonical: Account)

This section documents the **Accounts** table for SuiteAnalytics Connect (JDBC).

## Browsers and Reference Links

- Schema Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html#schematab
- Records Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html#scripttab
- Connect Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html#browsertab
- Analytics Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/account.html#analyticstab

## Accounts Table – Key Notes

- The **Other Custom Fields > Account** custom field is available for the Accounts table.
- To obtain the subsidiaries for accounts, use the **Account_subsidiary_map** table.
- JOIN to transactionLine using: `transactionLine.account_id = Account.account_id`

## Accounts – Columns

| Name | Type | Length | Precision | Scale | References | In | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| account_extid | VARCHAR2 | 255 |  |  |  |  | Account external ID |
| account_id | NUMBER |  | 39 | 0 |  |  | Account ID (Primary Key) |
| accountnumber | VARCHAR2 | 60 |  |  |  |  | Account number |
| cashflow_rate_type | VARCHAR2 | 10 |  |  |  |  | Cash flow rate type |
| category_1099_misc | VARCHAR2 | 60 |  |  |  |  | 1099-MISC category |
| category_1099_misc_mthreshold | NUMBER |  | 20 | 2 |  |  | 1099-MISC category threshold |
| class_id | NUMBER |  | 39 | 0 | class_id | Classes | Restrict to class |
| currency_id | NUMBER |  | 39 | 0 | currency_id | Currencies | Currency ID |
| date_last_modified | TIMESTAMP |  |  |  |  |  | Date last modified |
| deferral_account_id | NUMBER |  | 39 | 0 | account_id | Accounts | Deferral account ID |
| department_id | NUMBER |  | 39 | 0 | department_id | Departments | Restrict to department |
| description | VARCHAR2 | 25 |  |  |  |  | Description |
| full_description | VARCHAR2 | 60 |  |  |  |  | Full description |
| full_name | VARCHAR2 | 4000 |  |  |  |  | Full name |
| general_rate_type | VARCHAR2 | 10 |  |  |  |  | General rate type |
| is_balancesheet | VARCHAR2 | 1 |  |  |  |  | Is balance sheet |
| is_included_in_elimination | VARCHAR2 | 1 |  |  |  |  | Include in elimination |
| is_included_in_reval | VARCHAR2 | 1 |  |  |  |  | Include in revaluation |
| is_including_child_subs | VARCHAR2 | 3 |  |  |  |  | Whether includes child subsidiaries |
| is_leftside | VARCHAR2 | 1 |  |  |  |  | Is debit |
| is_summary | VARCHAR2 | 3 |  |  |  |  | Whether is a summary account |
| isinactive | VARCHAR2 | 3 |  |  |  |  | Account is inactive |
| legal_name | VARCHAR2 | 400 |  |  |  |  | Legal name |
| location_id | NUMBER |  | 39 | 0 | location_id | Locations | Restrict to location |
| name | VARCHAR2 | 93 |  |  |  |  | Name |
| openbalance | NUMBER |  | 39 | 0 |  |  | Opening balance |
| parent_id | NUMBER |  | 39 | 0 | account_id | Accounts | Subaccount of (parent account) |
| type_name | VARCHAR2 | 128 |  |  |  |  | Type name (e.g., Bank, Accounts Receivable, Income, Expense) |
| type_sequence | NUMBER |  | 39 | 0 |  |  | Type sequence |

## Primary key

| PK Column Name |
| --- |
| account_id |

## Foreign keys in this table

| FK Name | FK Column Name | PK Table Name | PK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| accounts_accounts_fk | deferral_account_id | Accounts | account_id | 1 |
| accounts_accounts_fk_2 | parent_id | Accounts | account_id | 1 |
| accounts_classes_fk | class_id | Classes | class_id | 1 |
| accounts_currencies_fk | currency_id | Currencies | currency_id | 1 |
| accounts_departments_fk | department_id | Departments | department_id | 1 |
| accounts_locations_fk | location_id | Locations | location_id | 1 |

## Foreign keys referencing this table

| FK Name | PK Column Name | FK Table Name | FK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| Transaction_lines_accounts_fk | account_id | Transaction_lines | account_id | 1 |
| Transaction_history_accounts_fk | account_id | Transaction_history | account_id | 1 |
| Transactions_accounts_fk | account_id | Transactions | acct_corp_card_expenses_id | 1 |
| Budget_accounts_fk | account_id | Budget | account_id | 1 |
| Account_activity_accounts_fk | account_id | Account_activity | account_id | 1 |
| Account_period_activity_accounts_fk | account_id | Account_period_activity | account_id | 1 |

## This table is included in the following domains

| Domains |
| --- |
| Expense_amortization |
| General_accounting |
| Invoice_with_amortization |
| Multibooks |
| Revenue_recognition |

## Common JOIN Pattern with Transaction_lines

```sql
SELECT 
  T.transaction_id,
  T.tranid,
  T.trandate,
  TL.transaction_line_id,
  TL.amount,
  A.account_id,
  A.accountnumber,
  A.name AS account_name,
  A.type_name AS account_type
FROM transaction T
INNER JOIN transactionLine TL ON T.transaction_id = TL.transaction_id
INNER JOIN Account A ON TL.account_id = A.account_id
WHERE <conditions>
```

Generated on 2024-11-25 for version 2024.2

---

# Customers

This section documents the **Customers** table for SuiteAnalytics Connect (JDBC).

## Browsers and Reference Links

- Schema Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/customer.html#schematab
- Records Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/customer.html#scripttab
- Connect Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/customer.html#browsertab
- Analytics Browser: https://system.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2024_2/odbc/record/customer.html#analyticstab

## Customers Table – Key Notes

- The **Entity Fields** custom field is available for the Customers table.
- JOIN to transaction using: `transaction.entity_id = Customers.customer_id`
- JOIN to transactionLine using: `transactionLine.company_id = Customers.customer_id`

## Customers – Columns

| Name | Type | Length | Precision | Scale | References | In | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accountnumber | VARCHAR2 | 99 |  |  |  |  | Account number |
| alcohol_recipient_type | VARCHAR2 | 32 |  |  |  |  | Alcohol recipient type |
| allow_task_time_for_allocation | VARCHAR2 | 3 |  |  |  |  | Allow task time for allocation |
| altemail | VARCHAR2 | 254 |  |  |  |  | Alternate email address |
| alternate_contact_id | NUMBER |  | 39 | 0 | contact_id | Contacts | Alternate contact |
| altphone | VARCHAR2 | 100 |  |  |  |  | Alternate phone |
| amount_complete | NUMBER |  | 5 | 2 |  |  | Amount complete |
| billaddress | VARCHAR2 | 999 |  |  |  |  | Billing address |
| billing_rate_card_id | NUMBER |  | 39 | 0 | billing_rate_card_id | Billing_rate_cards | Billing rate card ID |
| billing_schedule_id | NUMBER |  | 39 | 0 | billing_schedule_id | Billing_schedule_descriptions | Billing schedule ID |
| billing_schedule_type | VARCHAR2 | 60 |  |  |  |  | Billing type |
| billing_transaction_type | VARCHAR2 | 192 |  |  |  |  | Billing transaction type |
| calculated_end | TIMESTAMP |  |  |  |  |  | Estimated end date |
| category_0 | VARCHAR2 | 30 |  |  |  |  | Status (Customer Stage) |
| city | VARCHAR2 | 50 |  |  |  |  | City |
| comments | VARCHAR2 | 4000 |  |  |  |  | Comments |
| companyname | VARCHAR2 | 83 |  |  |  |  | Company name |
| consol_days_overdue | NUMBER |  | 39 | 0 |  |  | Consolidated days overdue |
| consol_deposit_balance | NUMBER |  | 39 | 0 |  |  | Consolidated deposit balance |
| consol_deposit_balance_foreign | NUMBER |  | 39 | 0 |  |  | Consolidated foreign currency deposit balance |
| consol_openbalance | NUMBER |  | 39 | 0 |  |  | Consolidated balance (sum of subcustomer balances in company currency) |
| consol_openbalance_foreign | NUMBER |  | 39 | 0 |  |  | Consolidated foreign currency balance (sum in parent customer's primary currency) |
| consol_unbilled_orders | NUMBER |  | 39 | 0 |  |  | Consolidated unbilled orders |
| consol_unbilled_orders_foreign | NUMBER |  | 39 | 0 |  |  | Consolidated foreign currency unbilled orders |
| converted_to_contact_id | NUMBER |  | 39 | 0 | entity_id | Entity | Contact the lead was converted to |
| converted_to_id | NUMBER |  | 39 | 0 | entity_id | Entity | Customer the lead was converted to |
| cost_estimate | NUMBER |  | 25 | 5 |  |  | Cost estimate |
| country | VARCHAR2 | 50 |  |  |  |  | Country |
| create_date | TIMESTAMP |  |  |  |  |  | Create date (GMT) |
| credithold | VARCHAR2 | 4 |  |  |  |  | Credit hold |
| creditlimit | NUMBER |  | 20 | 2 |  |  | Credit limit |
| currency_id | NUMBER |  | 39 | 0 | currency_id | Currencies | Currency ID |
| customer_extid | VARCHAR2 | 255 |  |  |  |  | Customer external ID |
| customer_id | NUMBER |  | 39 | 0 |  |  | Customer ID (Primary Key) |
| customer_type_id | NUMBER |  | 39 | 0 | customer_type_id | Customer_types | Category |
| date_calculated_start | TIMESTAMP |  |  |  |  |  | Calculated start date |
| date_closed | TIMESTAMP |  |  |  |  |  | Date closed (GMT) |
| date_convsersion | TIMESTAMP |  |  |  |  |  | Conversion from lead date (GMT) |
| date_first_order | TIMESTAMP |  |  |  |  |  | Date of first order (GMT) |
| date_first_sale | TIMESTAMP |  |  |  |  |  | Date of first sale (GMT) |
| date_gross_lead | TIMESTAMP |  |  |  |  |  | Gross lead date (GMT) |
| date_last_modified | TIMESTAMP |  |  |  |  |  | Date last modified |
| date_last_order | TIMESTAMP |  |  |  |  |  | Last sales order date (GMT) |
| date_last_sale | TIMESTAMP |  |  |  |  |  | Last sale (cash sale, invoice) date (GMT) |
| date_lead | TIMESTAMP |  |  |  |  |  | Lead date (GMT) |
| date_prospect | TIMESTAMP |  |  |  |  |  | Prospect date (GMT) |
| date_scheduled_end | TIMESTAMP |  |  |  |  |  | Scheduled end date |
| days_overdue | NUMBER |  | 39 | 0 |  |  | Days overdue (GMT) |
| default_order_priority | NUMBER |  | 20 | 2 |  |  | Default order priority |
| default_receivables_account_id | NUMBER |  | 39 | 0 | account_id | Accounts | Default receivables account |
| deposit_balance | NUMBER |  | 20 | 2 |  |  | Deposit balance |
| deposit_balance_foreign | NUMBER |  | 39 | 0 |  |  | Foreign currency deposit balance |
| email | VARCHAR2 | 254 |  |  |  |  | Email |
| expected_close | TIMESTAMP |  |  |  |  |  | Expected close date |
| fax | VARCHAR2 | 100 |  |  |  |  | Fax |
| first_sale_period_id | NUMBER |  | 39 | 0 | accounting_period_id | Accounting_periods | Accounting period of first sale |
| first_visit | TIMESTAMP |  |  |  |  |  | First visit |
| firstname | VARCHAR2 | 32 |  |  |  |  | First name |
| forecast_based_on_allocations | VARCHAR2 | 3 |  |  |  |  | Use Allocated Time for Forecast switch |
| forecast_charge_run_on_demand | VARCHAR2 | 3 |  |  |  |  | Forecast Charge Run on Demand switch |
| full_name | VARCHAR2 | 1800 |  |  |  |  | Full name |
| home_phone | VARCHAR2 | 100 |  |  |  |  | Home phone |
| is_exempt_time | VARCHAR2 | 3 |  |  |  |  | Exempt time |
| is_explicit_conversion | VARCHAR2 | 3 |  |  |  |  | Explicitly converted from lead |
| is_job | VARCHAR2 | 3 |  |  |  |  | Job |
| is_limit_time_to_assignees | VARCHAR2 | 3 |  |  |  |  | Only project resources can enter time/expenses |
| is_person | VARCHAR2 | 3 |  |  |  |  | Type (company or individual) |
| is_productive_time | VARCHAR2 | 3 |  |  |  |  | Is productive time |
| is_project_completely_billed | VARCHAR2 | 3 |  |  |  |  | Is project completely billed |
| is_source_item_from_brc | VARCHAR2 | 3 |  |  |  |  | Service item sourced from billing rate card |
| is_utilized_time | VARCHAR2 | 3 |  |  |  |  | Is utilized time |
| isemailhtml | VARCHAR2 | 3 |  |  |  |  | Email as HTML |
| isemailpdf | VARCHAR2 | 3 |  |  |  |  | Email as PDF |
| isinactive | VARCHAR2 | 3 |  |  |  |  | Customer is inactive |
| istaxable | VARCHAR2 | 3 |  |  |  |  | Taxable |
| job_end | TIMESTAMP |  |  |  |  |  | End date |
| job_start | TIMESTAMP |  |  |  |  |  | Start date |
| job_type_id | NUMBER |  | 39 | 0 | job_type_id | Job_types | Job type ID |
| labor_budget_from_allocations | VARCHAR2 | 3 |  |  |  |  | Labor budget from allocations |
| language_id | VARCHAR2 | 30 |  |  |  |  | Language ID |
| last_modified_date | TIMESTAMP |  |  |  |  |  | Last modified date (GMT) |
| last_sale_period_id | NUMBER |  | 39 | 0 | accounting_period_id | Accounting_periods | Accounting period of last sale |
| last_visit | TIMESTAMP |  |  |  |  |  | Last visit |
| lastname | VARCHAR2 | 32 |  |  |  |  | Last name |
| lead_source_id | NUMBER |  | 39 | 0 | campaign_id | Campaigns | Lead source ID |
| line1 | VARCHAR2 | 150 |  |  |  |  | Address line 1 |
| line2 | VARCHAR2 | 150 |  |  |  |  | Address line 2 |
| line3 | VARCHAR2 | 150 |  |  |  |  | Address line 3 |
| loginaccess | VARCHAR2 | 3 |  |  |  |  | Login Access |
| middlename | VARCHAR2 | 32 |  |  |  |  | Middle name |
| mobile_phone | VARCHAR2 | 100 |  |  |  |  | Mobile phone |
| multiple_price_id | NUMBER |  | 39 | 0 |  |  | Multiple price ID |
| name | VARCHAR2 | 83 |  |  |  |  | Name |
| openbalance | NUMBER |  | 39 | 0 |  |  | Balance |
| openbalance_foreign | NUMBER |  | 39 | 0 |  |  | Foreign currency balance |
| parent_id | NUMBER |  | 39 | 0 | entity_id | Entity | Child of (parent customer) |
| partner_id | NUMBER |  | 39 | 0 | partner_id | Partners | Partner ID |
| payment_terms_id | NUMBER |  | 39 | 0 | payment_terms_id | Payment_terms | Payment terms |
| phone | VARCHAR2 | 100 |  |  |  |  | Phone |
| primary_contact_id | NUMBER |  | 39 | 0 | contact_id | Contacts | Primary contact |
| print_on_check_as | VARCHAR2 | 83 |  |  |  |  | Print on check as |
| probability | NUMBER |  | 6 | 2 |  |  | Probability |
| project_expense_type_id | NUMBER |  | 39 | 0 | project_expense_type_id | Project_expense_types | Project expense type ID |
| project_manager_id | NUMBER |  | 39 | 0 | employee_id | Employees | Project manager ID |
| projected_end | TIMESTAMP |  |  |  |  |  | Projected end |
| referrer | VARCHAR2 | 4000 |  |  |  |  | Referrer |
| reminderdays | NUMBER |  | 39 | 0 |  |  | Reminder days |
| renewal | TIMESTAMP |  |  |  |  |  | Renewal |
| represents_subsidiary_id | NUMBER |  | 39 | 0 | subsidiary_id | Subsidiaries | Represents subsidiary ID |
| resalenumber | VARCHAR2 | 20 |  |  |  |  | Resale number |
| rev_rec_forecast_rule_id | NUMBER |  | 39 | 0 |  |  | Revenue recognition forecast rule ID |
| rev_rec_forecast_template | NUMBER |  | 39 | 0 | schedule_id | Revrecschedules | Revenue recognition forecast template |
| revenue_estimate | NUMBER |  | 25 | 5 |  |  | Revenue estimate |
| sales_rep_id | NUMBER |  | 39 | 0 | entity_id | Entity | Sales rep ID |
| sales_territory_id | NUMBER |  | 39 | 0 | territory_id | Territory | Sales territory ID |
| salutation | VARCHAR2 | 30 |  |  |  |  | Salutation |
| scheduling_method_id | VARCHAR2 | 15 |  |  |  |  | Project scheduling method |
| ship_complete | VARCHAR2 | 3 |  |  |  |  | Ship complete |
| shipaddress | VARCHAR2 | 999 |  |  |  |  | Shipping address |
| state | VARCHAR2 | 50 |  |  |  |  | State |
| status | VARCHAR2 | 199 |  |  |  |  | Status |
| status_descr | VARCHAR2 | 199 |  |  |  |  | Status description |
| status_probability | NUMBER |  | 6 | 2 |  |  | Status probability |
| status_read_only | VARCHAR2 | 3 |  |  |  |  | Read only status |
| subsidiary_id | NUMBER |  | 39 | 0 | subsidiary_id | Subsidiaries | Subsidiary ID |
| tax_item_id | NUMBER |  | 39 | 0 | item_id | Items | Tax item ID |
| third_party_acct | VARCHAR2 | 32 |  |  |  |  | Third party account |
| third_party_carrier | VARCHAR2 | 64 |  |  |  |  | Third party carrier |
| third_party_country | VARCHAR2 | 6 |  |  |  |  | Third party country |
| third_party_zip_code | VARCHAR2 | 10 |  |  |  |  | Third party zip code |
| time_approval_type_id | NUMBER |  | 39 | 0 | project_time_approval_type_id | Project_time_approval_types | Time approval type ID |
| top_level_parent_id | NUMBER |  | 39 | 0 | customer_id | Customers | Top level parent ID |
| unbilled_orders | NUMBER |  | 20 | 2 |  |  | Unbilled orders |
| unbilled_orders_foreign | NUMBER |  | 39 | 0 |  |  | Unbilled foreign currency orders |
| url | VARCHAR2 | 100 |  |  |  |  | Web address |
| use_calculated_billing_budget | VARCHAR2 | 3 |  |  |  |  | Use calculated billing budget |
| use_calculated_cost_budget | VARCHAR2 | 3 |  |  |  |  | Use calculated cost budget |
| use_percent_complete_override | VARCHAR2 | 3 |  |  |  |  | Use percent complete override |
| vat_reg_number | VARCHAR2 | 20 |  |  |  |  | VAT identification number |
| web_lead | VARCHAR2 | 3 |  |  |  |  | Web lead |
| zipcode | VARCHAR2 | 36 |  |  |  |  | Zip code |

## Primary key

| PK Column Name |
| --- |
| customer_id |

## Foreign keys in this table

| FK Name | FK Column Name | PK Table Name | PK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| customers_accounting_periods_fk | first_sale_period_id | Accounting_periods | accounting_period_id | 1 |
| customers_accounting_periods_fk_2 | last_sale_period_id | Accounting_periods | accounting_period_id | 1 |
| customers_accounts_fk | default_receivables_account_id | Accounts | account_id | 1 |
| customers_billing_rate_cards_fk | billing_rate_card_id | Billing_rate_cards | billing_rate_card_id | 1 |
| customers_billing_schedule_descriptions_fk | billing_schedule_id | Billing_schedule_descriptions | billing_schedule_id | 1 |
| customers_campaigns_fk | lead_source_id | Campaigns | campaign_id | 1 |
| customers_contacts_fk | primary_contact_id | Contacts | contact_id | 1 |
| customers_contacts_fk_2 | alternate_contact_id | Contacts | contact_id | 1 |
| customers_currencies_fk | currency_id | Currencies | currency_id | 1 |
| customers_customer_types_fk | customer_type_id | Customer_types | customer_type_id | 1 |
| customers_employees_fk | project_manager_id | Employees | employee_id | 1 |
| customers_entity_fk | converted_to_id | Entity | entity_id | 1 |
| customers_entity_fk_2 | converted_to_contact_id | Entity | entity_id | 1 |
| customers_entity_fk_3 | sales_rep_id | Entity | entity_id | 1 |
| customers_entity_fk_4 | parent_id | Entity | entity_id | 1 |
| customers_items_fk | tax_item_id | Items | item_id | 1 |
| customers_job_types_fk | job_type_id | Job_types | job_type_id | 1 |
| customers_partners_fk | partner_id | Partners | partner_id | 1 |
| customers_payment_terms_fk | payment_terms_id | Payment_terms | payment_terms_id | 1 |
| customers_project_expense_types_fk | project_expense_type_id | Project_expense_types | project_expense_type_id | 1 |
| customers_project_time_approval_types_fk | time_approval_type_id | Project_time_approval_types | project_time_approval_type_id | 1 |
| customers_revrecschedules_fk | rev_rec_forecast_template | Revrecschedules | schedule_id | 1 |
| customers_subsidiaries_fk | subsidiary_id | Subsidiaries | subsidiary_id | 1 |
| customers_subsidiaries_fk_2 | represents_subsidiary_id | Subsidiaries | subsidiary_id | 1 |
| customers_territory_fk | sales_territory_id | Territory | territory_id | 1 |
| top_level_customer_fk | top_level_parent_id | Customers | customer_id | 1 |

## Foreign keys referencing this table

| FK Name | PK Column Name | FK Table Name | FK Column Name | Key Seq |
| --- | --- | --- | --- | --- |
| Billing_rate_cards_customers_fk | customer_id | Billing_rate_cards | customer_id | 1 |
| Billing_subscriptions_customers_fk | customer_id | Billing_subscriptions | customer_id | 1 |
| Budget_customers_fk | customer_id | Budget | customer_id | 1 |
| Customer_currencies_customers_fk | customer_id | Customer_currencies | customer_id | 1 |
| Customer_subsidiary_map_customers_fk | customer_id | Customer_subsidiary_map | customer_id | 1 |
| Employee_time_customers_fk | customer_id | Employee_time | customer_id | 1 |
| Project_revenue_rules_customers_fk | customer_id | Project_revenue_rules | project_id | 1 |
| Purchase_charge_rules_customers_fk | customer_id | Purchase_charge_rules | project_id | 1 |
| Top_level_customer_fk | customer_id | Customers | top_level_parent_id | 1 |
| Transaction_lines_customers_fk | customer_id | Transaction_lines | company_id | 1 |
| Transactions_customers_fk | customer_id | Transactions | entity_id | 1 |

## This table is included in the following domains

| Domains |
| --- |
| Campaigns |
| Campaignevents |
| General_accounting |
| Multibooks |
| Revenue_recognition |

## Common JOIN Pattern with Transactions

```sql
SELECT 
  T.transaction_id,
  T.tranid,
  T.trandate,
  T.transaction_type,
  C.customer_id,
  C.companyname,
  C.name AS customer_name,
  C.email,
  C.phone,
  C.city,
  C.state,
  C.country
FROM transaction T
INNER JOIN transactionLine TL ON T.transaction_id = TL.transaction_id
INNER JOIN Customers C ON T.entity_id = C.customer_id
WHERE T.transaction_type IN ('CustInvc', 'SalesOrd', 'CashSale')
```

## Common JOIN Pattern with Transaction_lines (company_id)

```sql
SELECT 
  T.transaction_id,
  T.tranid,
  TL.transaction_line_id,
  TL.amount,
  C.customer_id,
  C.companyname,
  C.name AS customer_name
FROM transaction T
INNER JOIN transactionLine TL ON T.transaction_id = TL.transaction_id
INNER JOIN Customers C ON TL.company_id = C.customer_id
WHERE <conditions>
```

Generated on 2024-11-25 for version 2024.2
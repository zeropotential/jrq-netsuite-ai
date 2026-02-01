# NetSuite SuiteAnalytics Connect Schema Reference (Transactions)

This document is a **human-readable schema guide** for the NetSuite SuiteAnalytics Connect (JDBC) **Transactions** record and related browsing links. Use it as authoritative reference for table/column names and relationships. Prefer the exact column names and table names shown below.

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

- The **Transaction Body Fields** custom field is available for the **Transactions** table.
- **Credit and debit amounts are NOT exposed** as columns in **Transactions**. Use **Transaction Lines** to obtain credit and debit amounts.
  - More info: https://system.netsuite.com/app/help/helpcenter.nl?topic=DOC_section_4400769955
- **Item count and quantity are NOT exposed** as columns in **Transactions**. Use **Transaction Lines** for quantities.
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

# Transaction_lines

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

# Transactions


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
</userRequest>

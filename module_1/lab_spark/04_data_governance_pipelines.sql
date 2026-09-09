-- =============================================================================
-- Project Elevate: Module 1 Lab 4 — IAM Data Governance, Dynamic Masking & RLS
-- Target Project: pj-elevate-da | Region: us-central1
-- Governed Assets:
--   - CLS Target Table: pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2
--   - RLS Target Table: pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PART 1: Working Table Provisioning (Baseline Protection)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2` AS
SELECT * FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.silver_pos_transactions`;

CREATE OR REPLACE TABLE `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2` AS
SELECT * FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`;


-- -----------------------------------------------------------------------------
-- PART 3: Attach IAM Data Governance Tags to Table Columns via SQL DDL
-- -----------------------------------------------------------------------------
ALTER TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ALTER COLUMN customer_name
SET OPTIONS (data_governance_tags=[('pj-elevate-da/pii_classification', 'customer_name')]);

ALTER TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ALTER COLUMN customer_id
SET OPTIONS (data_governance_tags=[('pj-elevate-da/pii_classification', 'customer_id')]);

ALTER TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ALTER COLUMN total_amount_usd
SET OPTIONS (data_governance_tags=[('pj-elevate-da/pii_classification', 'financial_amount')]);

ALTER TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ALTER COLUMN total_amount
SET OPTIONS (data_governance_tags=[('pj-elevate-da/pii_classification', 'financial_amount')]);

ALTER TABLE `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ALTER COLUMN store_id
SET OPTIONS (data_governance_tags=[('pj-elevate-da/pii_classification', 'store_metadata')]);


-- -----------------------------------------------------------------------------
-- PART 5: Row-Level Security (RLS) Policies on Gold Inventory Ledger
-- -----------------------------------------------------------------------------
-- 1. Unrestricted nationwide access for Data Lead & Admin Runner
CREATE OR REPLACE ROW ACCESS POLICY rls_unrestricted_lead
ON `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2`
GRANT TO (
  'serviceAccount:sa-data-lead@pj-elevate-da.iam.gserviceaccount.com',
  'user:admin@watanabesei.altostrat.com'
)
FILTER USING (TRUE);

-- 2. Scoped territory access for Business Analyst (STORE_048 and STORE_009)
CREATE OR REPLACE ROW ACCESS POLICY rls_analyst_stores
ON `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2`
GRANT TO ('serviceAccount:sa-analyst@pj-elevate-da.iam.gserviceaccount.com')
FILTER USING (store_id IN ('STORE_048', 'STORE_009'));


-- -----------------------------------------------------------------------------
-- PART 6: Verification Queries (Executed under Service Account Impersonation)
-- -----------------------------------------------------------------------------
-- Persona 1: Data Lead Query (Unmasked Plaintext + All Stores)
SELECT store_id, transaction_id, customer_id, customer_name, total_amount_usd
FROM `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ORDER BY store_id, transaction_id
LIMIT 4;

SELECT DISTINCT store_id, city, store_name
FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2`
ORDER BY store_id
LIMIT 4;

-- Persona 2: Business Analyst Query (SHA256, Last 4, $0.00 Masking + Scoped Stores)
SELECT store_id, transaction_id, customer_id, customer_name, total_amount_usd
FROM `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`
ORDER BY store_id, transaction_id
LIMIT 4;

SELECT DISTINCT store_id, city, store_name
FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2`
ORDER BY store_id;

-- Persona 3: Restricted User Query (Protected Columns: 403 Forbidden; Ledger: 0 rows Default Deny)
-- SELECT store_id, transaction_id, customer_id, customer_name, total_amount_usd FROM `pj-elevate-da.cymbal_gold.aws_pos_transactions_gold2`;
SELECT count(*) as row_count
FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger2`;


-- -----------------------------------------------------------------------------
-- PART 7: Metadata Audit via INFORMATION_SCHEMA
-- -----------------------------------------------------------------------------
SELECT
    table_schema AS dataset_id,
    table_name,
    column_name,
    data_type,
    data_governance_tags[SAFE_OFFSET(0)].key AS tag_key,
    data_governance_tags[SAFE_OFFSET(0)].value AS tag_value
FROM `pj-elevate-da.cymbal_gold.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
WHERE ARRAY_LENGTH(data_governance_tags) > 0
ORDER BY table_name, column_name;

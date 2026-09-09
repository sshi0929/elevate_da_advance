-- =====================================================================================
-- Project Elevate — Cymbal Retail Modernization
-- Module 1 Lab 3: BigQuery Property Graph Analytics & Supply Chain Recall Traceability
-- Author: Google Cloud Customer Engineering (watanabesei@google.com)
-- Environment: pj-elevate-da | Region: us-central1
-- Datasets: cymbal-lakehouse.elevate_data (Federated Iceberg), cymbal_gold
-- Standard: ISO/IEC 39075 GQL & GoogleSQL Graph Extensions
-- =====================================================================================

-- #####################################################################################
-- PART 0: PRE-FLIGHT VERIFICATION OF RELATIONAL SOURCE TABLES
-- #####################################################################################

-- Verify 4 Node Tables in AWS Glue Iceberg Federated Dataset
SELECT 'supplier_nodes' AS table_name, COUNT(*) AS row_count FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.supplier_nodes`
UNION ALL
SELECT 'batch_lot_nodes', COUNT(*) FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.batch_lot_nodes`
UNION ALL
SELECT 'store_nodes', COUNT(*) FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.store_nodes`
UNION ALL
SELECT 'customer_nodes', COUNT(*) FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.customer_nodes`;

-- Verify 3 Edge Tables in AWS Glue Iceberg Federated Dataset
SELECT 'produced_batch_edges' AS table_name, COUNT(*) AS row_count FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.produced_batch_edges`
UNION ALL
SELECT 'shipped_to_edges', COUNT(*) FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.shipped_to_edges`
UNION ALL
SELECT 'sold_lot_to_customer_edges', COUNT(*) FROM `pj-elevate-da.cymbal-lakehouse.elevate_data.sold_lot_to_customer_edges`;


-- #####################################################################################
-- PART 1: PROPERTY GRAPH DDL REGISTRATION (BRD USE CASE 2.4)
-- #####################################################################################

-- Challenge 1.1: Declare Property Graph linking Suppliers, Batches, Stores, and Customers
CREATE OR REPLACE PROPERTY GRAPH `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
NODE TABLES (
  `pj-elevate-da.cymbal-lakehouse.elevate_data.supplier_nodes` AS Supplier
    KEY (supplier_id)
    LABEL Supplier
    PROPERTIES (supplier_id, facility_name, country, city, contact_email, risk_score, certified),
  `pj-elevate-da.cymbal-lakehouse.elevate_data.batch_lot_nodes` AS BatchLot
    KEY (batch_id)
    LABEL BatchLot
    PROPERTIES (batch_id, item_id, item_name, unit_price_usd, supplier_id, manufacturing_date, qa_inspection_status, harmful_material_defect, lot_size_units, currency, recall_status),
  `pj-elevate-da.cymbal-lakehouse.elevate_data.store_nodes` AS Store
    KEY (store_id)
    LABEL Store
    PROPERTIES (store_id, store_name, city, country, region, manager_name, overnight_cash_float_usd),
  `pj-elevate-da.cymbal-lakehouse.elevate_data.customer_nodes` AS Customer
    KEY (customer_id)
    LABEL Customer
    PROPERTIES (customer_id, name, loyalty_tier, email, phone_number, preferred_store, global_region)
)
EDGE TABLES (
  `pj-elevate-da.cymbal-lakehouse.elevate_data.produced_batch_edges` AS PRODUCED_BATCH
    KEY (edge_id)
    SOURCE KEY (source_supplier_id) REFERENCES Supplier (supplier_id)
    DESTINATION KEY (target_batch_id) REFERENCES BatchLot (batch_id)
    LABEL PRODUCED_BATCH
    PROPERTIES (production_date, qc_status),
  `pj-elevate-da.cymbal-lakehouse.elevate_data.shipped_to_edges` AS SHIPPED_TO
    KEY (edge_id)
    SOURCE KEY (source_batch_id) REFERENCES BatchLot (batch_id)
    DESTINATION KEY (target_store_id) REFERENCES Store (store_id)
    LABEL SHIPPED_TO
    PROPERTIES (quantity_shipped, shipment_date),
  `pj-elevate-da.cymbal-lakehouse.elevate_data.sold_lot_to_customer_edges` AS PURCHASED_LOT_BY_CUSTOMER
    KEY (edge_id)
    SOURCE KEY (batch_id) REFERENCES BatchLot (batch_id)
    DESTINATION KEY (target_customer_id) REFERENCES Customer (customer_id)
    LABEL PURCHASED_LOT_BY_CUSTOMER
    PROPERTIES (store_id, transaction_id, purchase_timestamp, serial_number, unit_price_usd, currency, payment_method, exposure_flag)
);


-- #####################################################################################
-- PART 2: GOOGLESQL GQL MULTI-HOP TRAVERSAL & GRAPH PATTERN MATCHING
-- #####################################################################################

-- -------------------------------------------------------------------------------------
-- Challenge 2.1: Variable-Length Distribution Routing & Path Extraction
-- Traces 1-3 shipment hops from batch lots to flagship retail stores
-- -------------------------------------------------------------------------------------
GRAPH `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
MATCH p = (lot:BatchLot)-[s:SHIPPED_TO]->{1, 3}(store:Store)
RETURN
  lot.batch_id,
  lot.item_id,
  lot.item_name,
  store.store_id,
  store.store_name,
  store.city,
  store.country,
  PATH_LENGTH(p) AS distribution_hops,
  TO_JSON(p) AS shipment_path
ORDER BY lot.batch_id, store.store_id;

-- -------------------------------------------------------------------------------------
-- Challenge 2.2: High-Risk Supplier to VIP Loyalty Customer Recall Triage (BRD 2.4)
-- Multi-hop path: (Supplier) -> (BatchLot) -> (Customer)
-- Filters: risk_score >= 0.75, VIP tiers (PLATINUM/GOLD), harmful material/recall flags
-- -------------------------------------------------------------------------------------
GRAPH `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
MATCH (sup:Supplier)-[:PRODUCED_BATCH]->(lot:BatchLot)-[sale:PURCHASED_LOT_BY_CUSTOMER]->(cust:Customer)
WHERE sup.risk_score >= 0.75
  AND cust.loyalty_tier IN ('PLATINUM', 'GOLD')
  AND (
    lot.qa_inspection_status = 'FLAGGED_HARMFUL_MATERIAL'
    OR lot.recall_status LIKE '%RECALL%'
    OR sale.exposure_flag = 'CONTAMINATED_HARMFUL'
  )
RETURN
  cust.customer_id,
  cust.name AS customer_name,
  cust.loyalty_tier,
  cust.email AS customer_email,
  cust.phone_number AS customer_phone,
  cust.global_region,
  lot.batch_id,
  lot.item_id,
  lot.item_name,
  lot.harmful_material_defect,
  lot.recall_status,
  sale.serial_number,
  sale.transaction_id,
  sale.purchase_timestamp,
  sup.supplier_id,
  sup.facility_name AS supplier_facility,
  sup.risk_score AS supplier_risk_score
ORDER BY cust.loyalty_tier DESC, sup.risk_score DESC, cust.name ASC;

-- -------------------------------------------------------------------------------------
-- Challenge 2.3: Indirect Customer Exposure & Supplier Blast Radius (Diamond Match)
-- Diamond topology: (c1) <- (b1) <- (Supplier) -> (b2) -> (c2)
-- -------------------------------------------------------------------------------------
GRAPH `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
MATCH (c1:Customer {customer_id: 'CUST_30697'})<-[:PURCHASED_LOT_BY_CUSTOMER]-(b1:BatchLot)<-[:PRODUCED_BATCH]-(sup:Supplier)-[:PRODUCED_BATCH]->(b2:BatchLot)-[:PURCHASED_LOT_BY_CUSTOMER]->(c2:Customer)
WHERE sup.risk_score >= 0.75 AND c1.customer_id != c2.customer_id
RETURN
  c1.customer_id AS index_customer_id,
  c1.name AS index_customer_name,
  b1.batch_id AS index_batch_id,
  b1.item_name AS index_product_name,
  sup.supplier_id,
  sup.facility_name AS common_supplier_facility,
  sup.risk_score AS supplier_risk_score,
  b2.batch_id AS secondary_batch_id,
  b2.item_name AS secondary_product_name,
  c2.customer_id AS secondary_customer_id,
  c2.name AS secondary_customer_name,
  c2.loyalty_tier AS secondary_loyalty_tier,
  c2.email AS secondary_customer_email,
  c2.phone_number AS secondary_customer_phone;


-- #####################################################################################
-- PART 3: AUTOMATED SAFETY RECALL AUDIT & RELATIONAL INTEGRATION (GRAPH_TABLE)
-- #####################################################################################

-- -------------------------------------------------------------------------------------
-- Challenge 3.1: Emergency Recall Contact Ledger via GRAPH_TABLE()
-- Extracts impacted hardware serials and customer contacts for contaminated batch
-- -------------------------------------------------------------------------------------
SELECT
  batch_id,
  harmful_material_defect,
  item_name,
  unit_price_usd,
  customer_id,
  customer_name,
  global_region,
  email,
  phone_number,
  store_id,
  transaction_id,
  purchase_timestamp,
  serial_number
FROM GRAPH_TABLE(
  `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
  MATCH (lot:BatchLot)-[sale:PURCHASED_LOT_BY_CUSTOMER]->(cust:Customer)
  WHERE lot.batch_id = 'LOT-202505-PROD4691-01'
    AND lot.qa_inspection_status = 'FLAGGED_HARMFUL_MATERIAL'
  COLUMNS (
    lot.batch_id,
    lot.harmful_material_defect,
    lot.item_name,
    lot.unit_price_usd,
    cust.customer_id,
    cust.name AS customer_name,
    cust.global_region,
    cust.email,
    cust.phone_number,
    sale.store_id,
    sale.transaction_id,
    sale.purchase_timestamp,
    sale.serial_number
  )
)
ORDER BY purchase_timestamp DESC;

-- -------------------------------------------------------------------------------------
-- Challenge 3.2: Supplier QA Defect Rate & Quality Scorecard (BRD 2.4 Prompt 2)
-- Combines GRAPH_TABLE with SQL GROUP BY aggregations for supplier quality scoring
-- -------------------------------------------------------------------------------------
SELECT
  supplier_id,
  facility_name,
  country,
  risk_score,
  COUNT(batch_id) AS total_lots_produced,
  COUNTIF(qa_inspection_status = 'PASSED_CLEAN') AS passed_clean_lots,
  COUNTIF(qa_inspection_status = 'FLAGGED_HARMFUL_MATERIAL') AS flagged_harmful_lots,
  ROUND(100.0 * COUNTIF(qa_inspection_status = 'FLAGGED_HARMFUL_MATERIAL') / COUNT(batch_id), 2) AS defect_rate_pct
FROM GRAPH_TABLE(
  `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
  MATCH (sup:Supplier)-[:PRODUCED_BATCH]->(lot:BatchLot)
  COLUMNS (
    sup.supplier_id,
    sup.facility_name,
    sup.country,
    sup.risk_score,
    lot.batch_id,
    lot.qa_inspection_status
  )
)
GROUP BY supplier_id, facility_name, country, risk_score
ORDER BY defect_rate_pct DESC, total_lots_produced DESC;

-- -------------------------------------------------------------------------------------
-- Challenge 3.3: Comprehensive 360° Supply Chain Recall Traceability View (BRD 2.4 Prompt 1)
-- Relational Gold View bridging graph pattern matching with downstream BI & GenAI
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `pj-elevate-da.cymbal_gold.supply_chain_recall_traceability_360` AS
SELECT
  g.transaction_id,
  g.hardware_serial_number,
  g.purchase_timestamp,
  g.product_sku,
  g.product_name,
  g.unit_price_usd,
  g.currency,
  g.is_active_recall,
  g.qa_inspection_status,
  g.defect_description,
  g.batch_recall_status,
  g.supplier_risk_category,
  g.supplier_id,
  g.supplier_facility,
  g.supplier_country,
  g.supplier_risk_score,
  g.is_supplier_certified,
  g.batch_id,
  g.manufacturing_date,
  g.store_id,
  s.store_name,
  s.city AS store_city,
  s.country AS store_country,
  s.region AS store_region,
  g.customer_id,
  g.customer_name,
  g.customer_loyalty_tier,
  g.customer_email,
  g.customer_phone,
  g.customer_region
FROM GRAPH_TABLE(
  `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph`
  MATCH (sup:Supplier)-[:PRODUCED_BATCH]->(lot:BatchLot)-[sale:PURCHASED_LOT_BY_CUSTOMER]->(cust:Customer)
  COLUMNS (
    sale.transaction_id,
    sale.serial_number AS hardware_serial_number,
    sale.purchase_timestamp,
    lot.item_id AS product_sku,
    lot.item_name AS product_name,
    sale.unit_price_usd,
    sale.currency,
    (
      lot.qa_inspection_status = 'FLAGGED_HARMFUL_MATERIAL'
      OR lot.recall_status LIKE '%RECALL%'
      OR sale.exposure_flag = 'TRUE'
      OR sale.exposure_flag = 'CONTAMINATED_HARMFUL'
    ) AS is_active_recall,
    lot.qa_inspection_status,
    lot.harmful_material_defect AS defect_description,
    lot.recall_status AS batch_recall_status,
    CASE
      WHEN sup.risk_score >= 0.75 THEN 'CRITICAL_HIGH_RISK'
      WHEN sup.risk_score >= 0.30 THEN 'MODERATE_RISK'
      ELSE 'LOW_RISK'
    END AS supplier_risk_category,
    sup.supplier_id,
    sup.facility_name AS supplier_facility,
    sup.country AS supplier_country,
    sup.risk_score AS supplier_risk_score,
    sup.certified AS is_supplier_certified,
    lot.batch_id,
    lot.manufacturing_date,
    sale.store_id,
    cust.customer_id,
    cust.name AS customer_name,
    cust.loyalty_tier AS customer_loyalty_tier,
    cust.email AS customer_email,
    cust.phone_number AS customer_phone,
    cust.global_region AS customer_region
  )
) AS g
LEFT JOIN `pj-elevate-da.cymbal-lakehouse.elevate_data.store_nodes` AS s
  ON g.store_id = s.store_id;

-- -------------------------------------------------------------------------------------
-- Challenge 3.3 Verification Query: Active Recall Dispatch Query
-- -------------------------------------------------------------------------------------
SELECT
  transaction_id,
  hardware_serial_number,
  product_name,
  batch_id,
  customer_id,
  customer_name,
  customer_loyalty_tier,
  customer_email,
  customer_phone,
  store_id,
  store_name,
  store_city,
  store_country,
  is_active_recall,
  supplier_risk_category
FROM `pj-elevate-da.cymbal_gold.supply_chain_recall_traceability_360`
WHERE is_active_recall = TRUE
  AND batch_id = 'LOT-202505-PROD4691-01'
ORDER BY purchase_timestamp DESC;

-- =====================================================================================
-- Project Elevate — Cymbal Retail Modernization
-- Module 1 Lab 2: Multimodal Document RAG & Native BigQuery AI Intelligence
-- Covers: Lab 2a (POS Manuals RAG) & Lab 2b (Warranty Dark Data Intelligence)
-- Author: Google Cloud Customer Engineering (watanabesei@google.com)
-- Environment: pj-elevate-da | Region: us-central1
-- =====================================================================================

-- #####################################################################################
-- LAB 2A: MULTIMODAL POS HARDWARE MANUAL INTELLIGENCE & CONVERSATIONAL RAG
-- #####################################################################################

-- -------------------------------------------------------------------------------------
-- Challenge 1.1: Create External Object Table over POS Guide PDFs
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE EXTERNAL TABLE `pj-elevate-da.module1_unstructureddata.pos_manual_generic_pdfs_objects`
WITH CONNECTION `pj-elevate-da.us-central1.biglake-iceberg-connection`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://pj-elevate-da-module1-bucket/store_pos_manual_generic/*'],
  metadata_cache_mode = 'AUTOMATIC',
  max_staleness = INTERVAL 1 DAY
);

-- -------------------------------------------------------------------------------------
-- Challenge 1.2: Register Remote Foundation Model (gemini-3.5-flash)
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE MODEL `pj-elevate-da.cymbal_gold.gemini_pos_manual_extractor`
REMOTE WITH CONNECTION `pj-elevate-da.us-central1.biglake-iceberg-connection`
OPTIONS (
  endpoint = 'gemini-3.5-flash',
  use_global_endpoint = true
);

-- -------------------------------------------------------------------------------------
-- Challenge 1.3: Single-Document Multimodal Smoke Test (Toshiba TCx 810 Guide)
-- -------------------------------------------------------------------------------------
SELECT
  uri,
  AI.GENERATE(
    (
      'Read the attached POS guide PDF. Reply with ONLY the Document Title, Terminal Equipment Covered, and Document Part Number exactly as printed. If unreadable, reply CANNOT_READ_FILE.',
      ref
    ),
    connection_id => 'pj-elevate-da.us-central1.biglake-iceberg-connection',
    endpoint => 'https://aiplatform.googleapis.com/v1/projects/pj-elevate-da/locations/global/publishers/google/models/gemini-3.5-flash'
  ) AS smoke_test_result
FROM `pj-elevate-da.module1_unstructureddata.pos_manual_generic_pdfs_objects`
WHERE uri LIKE '%Toshiba_TCx_810_Guide.pdf'
LIMIT 1;

-- -------------------------------------------------------------------------------------
-- Challenge 2.1: Full Document Multimodal Extraction with AI.GENERATE_TABLE
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `pj-elevate-da.module1_unstructureddata.pos_manual_generic_sections_extracted` AS
WITH extracted AS (
  SELECT
    source_pdf_uri,
    document_filename,
    document_title,
    document_part_no,
    equipment_covered,
    system_specifications,
    ports_and_power_budgets,
    fru_service_procedures,
    diagnostics_and_error_codes,
    software_and_os_stacks,
    offline_and_compliance_rules,
    extracted_full_text
  FROM AI.GENERATE_TABLE(
    MODEL `pj-elevate-da.cymbal_gold.gemini_pos_manual_extractor`,
    (
      SELECT
        (
          'You are an expert POS hardware systems engineer. Perform a comprehensive, exhaustive technical extraction of the attached POS hardware guide PDF. Extract and populate every field in full technical detail without omitting any values:\n' ||
          '- document_title: Full exact manual title as printed.\n' ||
          '- document_part_no: Hardware manual part number.\n' ||
          '- equipment_covered: Specific terminal models, machine types, and submodels.\n' ||
          '- system_specifications: Complete CPU, chipset, RAM capacities/frequencies, display resolutions/touch controllers, IP dust/water ingress ratings, thermal/operating envelopes.\n' ||
          '- ports_and_power_budgets: Every physical port, PoweredUSB (24V/12V) allocations, pinouts, cash drawer interfaces, power supply wattage limits.\n' ||
          '- fru_service_procedures: Step-by-step Field Replaceable Unit (FRU) replacement procedures, SSD/RAM replacement steps, torque specifications (N-cm / in-lb), fastener types, ESD safety procedures.\n' ||
          '- diagnostics_and_error_codes: Diagnostic LED patterns, POST beep codes, BIOS recovery procedures, error code tables with exact meanings and corrective actions.\n' ||
          '- software_and_os_stacks: Supported operating systems, drivers, OPOS/JPOS/UPOS platforms, firmware update utilities.\n' ||
          '- offline_and_compliance_rules: Offline transaction ceilings, store-and-forward rules, PCI-DSS compliance, encryption requirements, Whole-Unit Exchange (WUE) SOP.\n' ||
          '- extracted_full_text: Complete, detailed textual transcription of the document content.\n\n' ||
          'Do not summarize or abbreviate. Retain all exact model numbers, torque values, hex error codes, and step-by-step procedures.',
          ref
        ) AS prompt,
        uri AS source_pdf_uri,
        REGEXP_EXTRACT(uri, r'([^/]+)\.pdf$') AS document_filename
      FROM `pj-elevate-da.module1_unstructureddata.pos_manual_generic_pdfs_objects`
      WHERE uri LIKE '%.pdf'
    ),
    STRUCT(
      '''
      document_title STRING,
      document_part_no STRING,
      equipment_covered STRING,
      system_specifications STRING,
      ports_and_power_budgets STRING,
      fru_service_procedures STRING,
      diagnostics_and_error_codes STRING,
      software_and_os_stacks STRING,
      offline_and_compliance_rules STRING,
      extracted_full_text STRING
      ''' AS output_schema,
      8192 AS max_output_tokens,
      0.0 AS temperature
    )
  )
)
SELECT
  source_pdf_uri,
  document_filename,
  document_title,
  document_part_no,
  equipment_covered,
  system_specifications,
  ports_and_power_budgets,
  fru_service_procedures,
  diagnostics_and_error_codes,
  software_and_os_stacks,
  offline_and_compliance_rules,
  extracted_full_text,
  CONCAT(
    'DOCUMENT: ', IFNULL(document_title, ''), ' (Part No: ', IFNULL(document_part_no, ''), ')\n',
    'EQUIPMENT COVERED: ', IFNULL(equipment_covered, ''), '\n\n',
    '### SYSTEM SPECIFICATIONS\n', IFNULL(system_specifications, ''), '\n\n',
    '### PORTS AND POWER BUDGETS\n', IFNULL(ports_and_power_budgets, ''), '\n\n',
    '### FRU SERVICE PROCEDURES\n', IFNULL(fru_service_procedures, ''), '\n\n',
    '### DIAGNOSTICS AND ERROR CODES\n', IFNULL(diagnostics_and_error_codes, ''), '\n\n',
    '### SOFTWARE AND OS STACKS\n', IFNULL(software_and_os_stacks, ''), '\n\n',
    '### OFFLINE AND COMPLIANCE RULES\n', IFNULL(offline_and_compliance_rules, ''), '\n\n',
    '### FULL EXTRACTED TEXT\n', IFNULL(extracted_full_text, '')
  ) AS extracted_full_content
FROM extracted;

-- -------------------------------------------------------------------------------------
-- Challenge 3.1: Materialize 768-dim Dense Vector Embeddings (text-embedding-005)
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `pj-elevate-da.cymbal_gold.pos_manual_embeddings` AS
SELECT
  source_pdf_uri,
  document_filename,
  document_title,
  document_part_no,
  equipment_covered,
  extracted_full_content,
  text_embedding AS embedding
FROM ML.GENERATE_EMBEDDING(
  MODEL `pj-elevate-da.cymbal_gold.text_embedding_model`,
  (
    SELECT
      source_pdf_uri,
      document_filename,
      document_title,
      document_part_no,
      equipment_covered,
      extracted_full_content,
      extracted_full_content AS content
    FROM `pj-elevate-da.module1_unstructureddata.pos_manual_generic_sections_extracted`
  ),
  STRUCT(TRUE AS flatten_json_output)
);

-- -------------------------------------------------------------------------------------
-- Challenge 3.2: Perform Semantic Similarity Search with VECTOR_SEARCH (Cosine Distance)
-- -------------------------------------------------------------------------------------
SELECT
  base.document_filename,
  base.document_title,
  base.document_part_no,
  ROUND(distance, 4) AS cosine_distance,
  SUBSTR(base.extracted_full_content, 1, 300) AS content_snippet
FROM VECTOR_SEARCH(
  TABLE `pj-elevate-da.cymbal_gold.pos_manual_embeddings`,
  'embedding',
  (
    SELECT ml_generate_embedding_result AS embedding
    FROM ML.GENERATE_EMBEDDING(
      MODEL `pj-elevate-da.cymbal_gold.text_embedding_model`,
      (SELECT 'Toshiba TCx 810 M.2 NVMe SSD replacement procedure, torque specifications, and ESD precautions' AS content),
      STRUCT(TRUE AS flatten_json_output)
    )
  ),
  top_k => 2,
  distance_type => 'COSINE'
);


-- #####################################################################################
-- LAB 2B: WARRANTY DARK DATA MULTIMODAL INTELLIGENCE & NATIVE SEMANTIC SEARCH
-- #####################################################################################

-- -------------------------------------------------------------------------------------
-- Challenge 1.1: Create External Object Table with Metadata Caching
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE EXTERNAL TABLE `pj-elevate-da.module1_unstructureddata.warranty_generic_pdfs_objects`
WITH CONNECTION `pj-elevate-da.us-central1.biglake-iceberg-connection`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://pj-elevate-da-module1-bucket/warranty_generic/*'],
  metadata_cache_mode = 'AUTOMATIC',
  max_staleness = INTERVAL 1 DAY
);

-- -------------------------------------------------------------------------------------
-- Challenge 1.2: Direct Zero-Shot Boolean Policy Evaluation (AI.IF)
-- -------------------------------------------------------------------------------------
SELECT
  REGEXP_EXTRACT(uri, r'([^/]+)\.pdf$') AS document_name,
  AI.IF(
    (
      'Does this warranty policy explicitly provide coverage for accidental damage, drops, or liquid spills? Reply true if covered, false if excluded.',
      ref
    ),
    connection_id => 'pj-elevate-da.us-central1.biglake-iceberg-connection',
    endpoint => 'https://aiplatform.googleapis.com/v1/projects/pj-elevate-da/locations/global/publishers/google/models/gemini-3.5-flash'
  ) AS has_accidental_damage_coverage,
  AI.IF(
    (
      'Does this warranty policy offer a full replacement option for defective units that cannot be serviced, or is it repair-only? Reply true if replacement is offered, false otherwise.',
      ref
    ),
    connection_id => 'pj-elevate-da.us-central1.biglake-iceberg-connection',
    endpoint => 'https://aiplatform.googleapis.com/v1/projects/pj-elevate-da/locations/global/publishers/google/models/gemini-3.5-flash'
  ) AS offers_replacement_option
FROM `pj-elevate-da.module1_unstructureddata.warranty_generic_pdfs_objects`
LIMIT 5;

-- -------------------------------------------------------------------------------------
-- Challenge 1.3: Zero-Shot Multimodal Taxonomy Classification (AI.CLASSIFY)
-- -------------------------------------------------------------------------------------
SELECT
  REGEXP_EXTRACT(uri, r'([^/]+)\.pdf$') AS document_name,
  AI.CLASSIFY(
    (
      'Classify this product warranty certificate into the most appropriate retail product taxonomy category.',
      ref
    ),
    categories => [
      'Smartphones & Tablets',
      'Laptops & Computing',
      'Audio & Headphones',
      'Wearables & Smartwatches',
      'Home & Kitchen Appliances',
      'Cameras & Imaging'
    ],
    connection_id => 'pj-elevate-da.us-central1.biglake-iceberg-connection',
    endpoint => 'https://aiplatform.googleapis.com/v1/projects/pj-elevate-da/locations/global/publishers/google/models/gemini-3.5-flash'
  ) AS product_category
FROM `pj-elevate-da.module1_unstructureddata.warranty_generic_pdfs_objects`
LIMIT 5;

-- -------------------------------------------------------------------------------------
-- Challenge 2.1: Full Document Multimodal Extraction with AI.GENERATE_TABLE
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE MODEL `pj-elevate-da.cymbal_gold.gemini_generic_warranty_extractor`
REMOTE WITH CONNECTION `pj-elevate-da.us-central1.biglake-iceberg-connection`
OPTIONS (
  endpoint = 'gemini-3.5-flash',
  use_global_endpoint = true
);

CREATE OR REPLACE TABLE `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted` AS
WITH extracted AS (
  SELECT
    source_pdf_uri,
    product_id,
    product_name,
    brand,
    category,
    retail_price_usd,
    warranty_duration_months,
    warranty_start,
    coverage_type,
    service_level,
    service_region,
    coverage_scope_details,
    exclusions_and_limitations,
    official_retailer_guarantee_and_sla,
    support_and_claims_process,
    support_url,
    support_email,
    extracted_full_text
  FROM AI.GENERATE_TABLE(
    MODEL `pj-elevate-da.cymbal_gold.gemini_generic_warranty_extractor`,
    (
      SELECT
        (
          'You are an expert warranty claims and compliance analyst. Perform a comprehensive, exhaustive extraction of the attached Cymbal Global Retail Care Official Product Warranty Certificate PDF. Extract and populate every field accurately according to the document layout:\n' ||
          '- product_id: The exact SKU / Product ID from the header band (e.g. prod_155).\n' ||
          '- product_name: Full official product model name as printed.\n' ||
          '- brand: Manufacturer / product brand.\n' ||
          '- category: Product retail category.\n' ||
          '- retail_price_usd: Clean numeric MSRP/retail price in USD (e.g. 299.99, omit currency signs).\n' ||
          '- warranty_duration_months: Warranty duration in months as an integer (e.g. 12, 24).\n' ||
          '- warranty_start: Warranty start conditions (e.g. date of retail purchase).\n' ||
          '- coverage_type: Type of coverage (e.g. Limited Hardware Warranty).\n' ||
          '- service_level: SLA / service level description.\n' ||
          '- service_region: Geographic validity footprint.\n' ||
          '- coverage_scope_details: Complete verbatim text of Section 1: Warranty Coverage & Protection Terms.\n' ||
          '- exclusions_and_limitations: Complete verbatim text of Section 2: Exclusions & Operating Limitations.\n' ||
          '- official_retailer_guarantee_and_sla: Complete verbatim text of Section 3: Official Authorized Retailer Guarantee & Seal.\n' ||
          '- support_and_claims_process: Customer support & claims instructions.\n' ||
          '- support_url: Official support website URL.\n' ||
          '- support_email: Support contact email address.\n' ||
          '- extracted_full_text: Complete verbatim text transcription of the entire document.',
          ref
        ) AS prompt,
        uri AS source_pdf_uri
      FROM `pj-elevate-da.module1_unstructureddata.warranty_generic_pdfs_objects`
      WHERE uri LIKE '%.pdf'
    ),
    STRUCT(
      '''
      product_id STRING,
      product_name STRING,
      brand STRING,
      category STRING,
      retail_price_usd FLOAT64,
      warranty_duration_months INT64,
      warranty_start STRING,
      coverage_type STRING,
      service_level STRING,
      service_region STRING,
      coverage_scope_details STRING,
      exclusions_and_limitations STRING,
      official_retailer_guarantee_and_sla STRING,
      support_and_claims_process STRING,
      support_url STRING,
      support_email STRING,
      extracted_full_text STRING
      ''' AS output_schema,
      8192 AS max_output_tokens,
      0.0 AS temperature
    )
  )
)
SELECT
  product_id,
  product_name,
  brand,
  category,
  retail_price_usd,
  warranty_duration_months,
  warranty_start,
  coverage_type,
  service_level,
  service_region,
  coverage_scope_details,
  exclusions_and_limitations,
  official_retailer_guarantee_and_sla,
  support_and_claims_process,
  support_url,
  support_email,
  CONCAT(
    'DOCUMENT: Cymbal Global Retail Care - Official Product Warranty Certificate\n',
    'SOURCE FILE: ', source_pdf_uri, '\n',
    'PRODUCT ID: ', IFNULL(product_id, ''), '\n',
    'PRODUCT NAME: ', IFNULL(product_name, ''), '\n',
    'BRAND: ', IFNULL(brand, ''), '\n',
    'CATEGORY: ', IFNULL(category, ''), '\n',
    'RETAIL PRICE USD: $', IFNULL(CAST(retail_price_usd AS STRING), ''), '\n',
    'WARRANTY DURATION: ', IFNULL(CAST(warranty_duration_months AS STRING), ''), ' Months\n',
    'WARRANTY START: ', IFNULL(warranty_start, ''), '\n',
    'COVERAGE TYPE: ', IFNULL(coverage_type, ''), '\n',
    'SERVICE LEVEL: ', IFNULL(service_level, ''), '\n',
    'SERVICE REGION: ', IFNULL(service_region, ''), '\n\n',
    '### SECTION 1: WARRANTY COVERAGE & PROTECTION TERMS\n', IFNULL(coverage_scope_details, ''), '\n\n',
    '### SECTION 2: EXCLUSIONS & OPERATING LIMITATIONS\n', IFNULL(exclusions_and_limitations, ''), '\n\n',
    '### SECTION 3: OFFICIAL AUTHORIZED RETAILER GUARANTEE & SEAL\n', IFNULL(official_retailer_guarantee_and_sla, ''), '\n\n',
    '### SUPPORT, CLAIMS & STATUTORY RIGHTS\n', IFNULL(support_and_claims_process, ''), '\n',
    'SUPPORT URL: ', IFNULL(support_url, ''), '\n',
    'SUPPORT EMAIL: ', IFNULL(support_email, ''), '\n\n',
    '### FULL EXTRACTED TEXT TRANSCRIPTION\n', IFNULL(extracted_full_text, '')
  ) AS extracted_full_content,
  source_pdf_uri
FROM extracted;

-- Quality Gate Assertion
SELECT
  COUNT(*)                                                AS total_rows,
  COUNTIF(product_name IS NULL OR product_name = 'N/A')   AS n_missing_name,
  COUNTIF(retail_price_usd IS NULL)                       AS n_missing_price,
  COUNTIF(warranty_duration_months IS NULL)               AS n_missing_duration,
  ROUND(AVG(LENGTH(extracted_full_content)))              AS avg_content_chars,
  MIN(LENGTH(extracted_full_content))                     AS min_content_chars,
  MAX(LENGTH(extracted_full_content))                     AS max_content_chars
FROM `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted`;

-- -------------------------------------------------------------------------------------
-- Challenge 3.1: Materialize Autonomous Vector Embeddings (GENERATED ALWAYS AS AI.EMBED)
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `pj-elevate-da.cymbal_gold.warranty_generic_pdf_chunk_embeddings` (
  product_id STRING,
  product_name STRING,
  brand STRING,
  category STRING,
  warranty_duration_months INT64,
  service_level STRING,
  source_pdf_uri STRING,
  extracted_full_content STRING,
  embedding STRUCT<result ARRAY<FLOAT64>, status STRING>
    GENERATED ALWAYS AS (AI.EMBED(
      extracted_full_content,
      connection_id => 'pj-elevate-da.us-central1.biglake-iceberg-connection',
      endpoint => 'text-embedding-005'
    )) STORED OPTIONS(asynchronous = TRUE)
);

INSERT INTO `pj-elevate-da.cymbal_gold.warranty_generic_pdf_chunk_embeddings` (
  product_id,
  product_name,
  brand,
  category,
  warranty_duration_months,
  service_level,
  source_pdf_uri,
  extracted_full_content
)
SELECT
  product_id,
  product_name,
  brand,
  category,
  warranty_duration_months,
  service_level,
  source_pdf_uri,
  extracted_full_content
FROM `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted`;

-- -------------------------------------------------------------------------------------
-- Challenge 3.2: Native Semantic Search Execution (AI.SEARCH)
-- -------------------------------------------------------------------------------------
SELECT
  ROUND(distance, 6) AS distance,
  base.product_id,
  base.product_name,
  base.brand,
  base.warranty_duration_months,
  base.service_level,
  SUBSTR(base.extracted_full_content, 1, 120) AS content_preview,
  base.source_pdf_uri
FROM AI.SEARCH(
  TABLE `pj-elevate-da.cymbal_gold.warranty_generic_pdf_chunk_embeddings`,
  'extracted_full_content',
  'What are the warranty coverage terms, replacement entitlements, and exclusions for OnePlus wireless earbuds?',
  top_k => 3,
  distance_type => 'COSINE'
)
ORDER BY distance;

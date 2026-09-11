from google.cloud import bigquery

client = bigquery.Client(project="pj-elevate-da", location="us-central1")

prompt = "What is the immediate field recovery protocol when a cashier encounters an ERR-PAY-4001 EMV contactless payment freeze, and how do we ensure the customer is not double-charged?"

sql = """
WITH query_emb AS (
  SELECT ml_generate_embedding_result AS embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `pj-elevate-da.cymbal_gold.text_embedding_model`,
    (SELECT @prompt AS content),
    STRUCT("RETRIEVAL_QUERY" AS task_type, TRUE AS flatten_json_output)
  )
),
vector_results AS (
  SELECT
    base.document_filename,
    base.document_title,
    base.source_pdf_uri,
    base.equipment_covered,
    base.chunk_index,
    base.chunk_content,
    ROUND(1 - distance, 4) AS similarity_score
  FROM VECTOR_SEARCH(
    TABLE `pj-elevate-da.cymbal_gold.pos_manual_chunk_embeddings`,
    "embedding",
    TABLE query_emb,
    top_k => 3,
    distance_type => "COSINE"
  )
),
stitched AS (
  SELECT
    v.document_filename,
    v.document_title,
    v.equipment_covered,
    v.source_pdf_uri,
    v.similarity_score,
    v.chunk_index AS matched_chunk_index,
    STRING_AGG(c.chunk_content, '\\n' ORDER BY c.chunk_index ASC) AS stitched_content
  FROM vector_results v
  JOIN `pj-elevate-da.cymbal_gold.pos_manual_chunk_embeddings` c
    ON v.document_filename = c.document_filename
   AND c.chunk_index BETWEEN (v.chunk_index - 1) AND (v.chunk_index + 1)
  GROUP BY v.document_filename, v.document_title, v.equipment_covered, v.source_pdf_uri, v.similarity_score, v.chunk_index
)
SELECT * FROM stitched ORDER BY similarity_score DESC LIMIT 1;
"""

job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("prompt", "STRING", prompt)
    ]
)

for row in client.query(sql, job_config=job_config).result():
    print("Title:", row.document_title)
    print("Similarity Score:", row.similarity_score)
    print("Source URI:", row.source_pdf_uri)
    print("Contains ERR-PAY-4001?", "ERR-PAY-4001" in row.stitched_content)
    print("Sample Content:\n", row.stitched_content[:500])

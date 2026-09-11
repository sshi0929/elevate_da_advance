"""POS Hardware Troubleshooting RAG Tool for Cymbal Retail.

Queries fine-grained technical manual chunks in BigQuery using VECTOR_SEARCH,
adjacent context window stitching (N-1 to N+1), and full-text SEARCH fallback.
"""

import os
import re
import time
from google.cloud import bigquery

PROJECT_ID = os.getenv("PROJECT_ID", "pj-elevate-da")
LOCATION = os.getenv("LOCATION", "us-central1")
CHUNK_TABLE = f"`{PROJECT_ID}.cymbal_gold.pos_manual_chunk_embeddings`"
EMBEDDING_MODEL = f"`{PROJECT_ID}.cymbal_gold.text_embedding_model`"
SIMILARITY_THRESHOLD = 0.70


def _gcs_to_https(uri: str) -> str:
    """Converts a gs:// URI to a clickable HTTPS URL."""
    if uri and uri.startswith("gs://"):
        path = uri[5:]
        return f"https://storage.cloud.google.com/{path}"
    return uri


def pos_troubleshooting_rag_tool(query: str) -> str:
    """Performs semantic vector search and procedural runbook retrieval over certified POS terminal hardware manuals.

    Use this tool to retrieve official SOPs, hardware error codes (e.g. ERR-PAY-4001, ERR-DN-PRNT-24V),
    freeze recovery protocols, payment terminal maintenance, printer jams, and scanner troubleshooting.

    Args:
        query: Specific hardware fault, error code, or troubleshooting question.

    Returns:
        Full stitched procedural runbook with certified equipment metadata and clickable GCS manual link.
    """
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

    # 1. Primary Vector Search Query with Adjacent Chunk Stitching (N-1 to N+1)
    vector_sql = f"""
    WITH query_emb AS (
      SELECT ml_generate_embedding_result AS embedding
      FROM ML.GENERATE_EMBEDDING(
        MODEL {EMBEDDING_MODEL},
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
        TABLE {CHUNK_TABLE},
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
      JOIN {CHUNK_TABLE} c
        ON v.document_filename = c.document_filename
       AND c.chunk_index BETWEEN (v.chunk_index - 1) AND (v.chunk_index + 1)
      GROUP BY v.document_filename, v.document_title, v.equipment_covered, v.source_pdf_uri, v.similarity_score, v.chunk_index
    )
    SELECT * FROM stitched ORDER BY similarity_score DESC LIMIT 1;
    """

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prompt", "STRING", query)
                ]
            )
            query_job = client.query(vector_sql, job_config=job_config)
            rows = list(query_job.result())

            if rows:
                top_row = rows[0]
                similarity_score = float(top_row.similarity_score)

                # Check safety threshold
                if similarity_score >= SIMILARITY_THRESHOLD:
                    doc_link = _gcs_to_https(top_row.source_pdf_uri)
                    return (
                        f"### Certified POS Hardware SOP: {top_row.document_title}\n"
                        f"- **Equipment Covered:** {top_row.equipment_covered}\n"
                        f"- **Similarity Relevance:** {similarity_score:.4f} (Certified $\\ge {SIMILARITY_THRESHOLD}$)\n"
                        f"- **Official Documentation Link:** [{top_row.document_filename}]({doc_link})\n\n"
                        f"#### Procedural Troubleshooting Instructions:\n"
                        f"{top_row.stitched_content}\n"
                    )

            # If vector search score fell below threshold or returned no rows, attempt full-text SEARCH fallback
            # Extract potential error codes like ERR-PAY-4001, ERR-DN-PRNT-24V
            error_codes = re.findall(r'[A-Za-z0-9]+-[A-Za-z0-9-]+', query)
            search_token = error_codes[0] if error_codes else query

            fallback_sql = f"""
            WITH matches AS (
              SELECT
                document_filename,
                document_title,
                source_pdf_uri,
                equipment_covered,
                chunk_index,
                chunk_content,
                0.85 AS similarity_score
              FROM {CHUNK_TABLE}
              WHERE SEARCH(chunk_content, @token)
              LIMIT 1
            ),
            stitched AS (
              SELECT
                m.document_filename,
                m.document_title,
                m.equipment_covered,
                m.source_pdf_uri,
                m.similarity_score,
                STRING_AGG(c.chunk_content, '\\n' ORDER BY c.chunk_index ASC) AS stitched_content
              FROM matches m
              JOIN {CHUNK_TABLE} c
                ON m.document_filename = c.document_filename
               AND c.chunk_index BETWEEN (m.chunk_index - 1) AND (m.chunk_index + 1)
              GROUP BY m.document_filename, m.document_title, m.equipment_covered, m.source_pdf_uri, m.similarity_score
            )
            SELECT * FROM stitched;
            """
            fallback_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("token", "STRING", f"`{search_token}`")
                ]
            )
            fb_rows = list(client.query(fallback_sql, job_config=fallback_config).result())
            if fb_rows:
                fb_row = fb_rows[0]
                doc_link = _gcs_to_https(fb_row.source_pdf_uri)
                return (
                    f"### Certified POS Hardware SOP (Full-Text Search Match): {fb_row.document_title}\n"
                    f"- **Equipment Covered:** {fb_row.equipment_covered}\n"
                    f"- **Match Strategy:** Full-Text Search fallback for token `{search_token}`\n"
                    f"- **Official Documentation Link:** [{fb_row.document_filename}]({doc_link})\n\n"
                    f"#### Procedural Troubleshooting Instructions:\n"
                    f"{fb_row.stitched_content}\n"
                )

            # Neither vector search nor fallback matched above threshold
            return (
                f"Warning: No certified POS hardware troubleshooting runbook found matching query "
                f"(similarity score below safety threshold of {SIMILARITY_THRESHOLD}). "
                f"This hardware component or issue is out-of-scope for certified store POS manuals. "
                f"Please consult external maintenance or facilities support."
            )

        except Exception as e:
            if attempt == max_retries:
                return f"Error executing POS troubleshooting retrieval ({e}). Please contact Cymbal Field Support."
            time.sleep(2 ** attempt)

    return "Error: POS hardware troubleshooting service is temporarily unavailable."

# Rikaal Testing Results

## Overview

The existing Rikaal backend was run for the first time to verify the setup,
API, Qdrant integration, ingestion, semantic search, project scoping, and
chunking behavior.

---
## Ticket 3:

## 1. Qdrant

Qdrant was successfully started and verified.

**Version:** `v1.11.2`

Available services:

- REST API: `http://localhost:6333`
- Dashboard: `http://localhost:6333/dashboard`
- gRPC: `localhost:6334`

**Result:** PASS

---

## 2. Python Setup

A Python virtual environment was created and the project dependencies were
installed successfully using:

```bash
pip install -r requirements.txt
```
The all-MiniLM-L6-v2 embedding model was downloaded successfully on first
startup.

Result: PASS


## 3. Configuration:

```bash
Copy-Item .env.example .env
```

## 4. FAST API Startup:

```bash
uvicorn apps.backend.main:app --reload
```
The API documentation was available at:
http://localhost:8000/docs

Result: PASS

## 5. Health Check:

Endpoint:

GET /health

Response:
{
  "status": "ok"
}

Result: PASS

## 6. Ingestion:
The /ingest endpoint was tested with sample project knowledge.

Response:

{
  "ingested_chunks": 1,
  "project": "demo"
}

The text was successfully converted into an embedding and stored in Qdrant.

Result: PASS

## 7. Sementic Search:

The /search endpoint was tested using:

{
  "query": "how do we handle database access?",
  "project": "demo",
  "top_k": 5
}

The search returned the expected ingested chunk with a relevance score.

Example score:

0.40458113

Result: PASS

## 8. Project Scoping:

Project-level search was tested using two different projects.

Project a returned PostgreSQL-related knowledge.
Project b returned MongoDB-related knowledge.
Project a did not return project b knowledge.
Project b did not return project a knowledge.

This confirmed that search results are correctly scoped by project.

Result: PASS

## 9. Chunking:

The chunk_text() function was tested with a long document containing
100 sentences.

The chunking logic was corrected and tested again.

The final test produced:

Number of chunks: 10

The test confirmed:

Chunks remain in order.
Chunks have overlap.
All document content is present.
No content was skipped.

Verification:

All content present: True

Result: PASS

## 10. FastAPI Startup Deprecation:

The deprecated FastAPI startup event:

@app.on_event("startup")

was replaced with a lifespan handler.

The application continued to start successfully after the change.

Result: FIXED

## 11. Qdrant Search Deprecation

The deprecated Qdrant:

client.search()

usage was updated to the supported query API.

The /search endpoint was tested after the change and successfully returned
search results with relevance scores.

Result: FIXED

## 12. README:

The incorrect API startup command:

uvicorn app.main:app --reload

was corrected to:

uvicorn apps.backend.main:app --reload

Qdrant setup information was also updated to reflect the tested setup.

Result: UPDATED

## Ticket 5 — GitHub Ingestion Testing

## 1. Endpoint

Tested the new:

POST /ingest/github

Request format:
```json
{
  "repo": "owner/name",
  "branch": "main",
  "project": "default"
}
```

### 2. Public Repository Test

Verified GitHub repository ingestion using a public repository.

The endpoint:

1.Connects to the GitHub REST API using httpx
2.Lists repository files using the Git tree API
3.Selects only the root README.md and .md files under docs/
4.Fetches the selected file contents
5.Processes the content through the existing chunk_text and add_chunks pipeline
6.Stores the resulting chunks in Qdrant

Expected file selection:

README.md                 ✓ Ingested
docs/architecture.md     ✓ Ingested
docs/setup.md            ✓ Ingested

Result: No README or Markdown files under docs were found.

## 4. Chunk Metadata:

Verified that ingested chunks contain the required metadata:

1.source: github
2.project: <StrideWeek>
3.repo: <mzain-there/StrideWeek>
4.path: <file path>

This allows /search results to identify which repository and file the knowledge came from.

## 5. Re-ingestion / Duplicate Prevention:

Ingested the same repository twice using the same project.

First ingestion
Total chunks: 11
Second ingestion
Total chunks: 11

The Qdrant chunk count remained the same after the second ingestion.

This confirms that re-ingestion does not create duplicate chunks for the same project + repo combination.

## 6. Search Verification:

After ingestion, tested /search using:

{
  "query": "StrideWeeek use for what?",
  "project": "StridWeek"
}

Verified that the search response returns the relevant repository knowledge and includes the source file path.

## 7. GitHub Token:

Configured an optional GITHUB_TOKEN through .env for authenticated GitHub API requests.

The token is not committed to the repository.

.env.example contains only:
# GITHUB_TOKEN= your_github_token_here

## 8. Error Handling:

Verified handling for:

1.Invalid repository
2.Invalid branch
3.Repository with no eligible Markdown files
4.Oversized Markdown files

The endpoint returns a clear error/message instead of silently returning a successful response with zero chunks.

## 9. Final Verification:

Ticket 5 final verification:

Repository: mzain-there/rikaal
Project: rikaal
Search query: "why did we choose local embeddings"

Expected result:

Relevant content from the Rikaal README is returned.
The response identifies the source file/path.
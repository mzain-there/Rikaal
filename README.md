# Rikaal

The pre-flight knowledge layer for code agents. Brainstorm with your project's
full context (docs, decisions, code, discussions), then hand a clean, structured
prompt to your IDE coding agent — instead of stuffing its context with PDFs,
scattered `.md` files, and web searches.

This is the **Day 1 MVP skeleton**: ingest knowledge → retrieve it → brainstorm
over it → export a structured prompt. One project, local-first.

---

## What runs where

| Piece            | Tech                         | Cost                    |
|------------------|------------------------------|-------------------------|
| Vector DB        | Qdrant (Docker)              | free, local             |
| Embeddings       | `all-MiniLM-L6-v2` (local)   | free                    |
| Brainstorm LLM   | Claude via AWS Bedrock       | pay-per-use (chat only) |
| API              | FastAPI                      | free                    |

The **ingest + search** loop runs with zero AWS. You only need Bedrock for
`/chat` and `/finalize`.

---

## Run it locally (≈15 min)

### 1. Start Qdrant

#### Option A — Manual Qdrant

Rikaal uses Qdrant as its vector database.

The setup has been tested with Qdrant:

- Qdrant server: `v1.11.2`
- Python client: `qdrant-client==1.11.2`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

You can run Qdrant using either Docker or a standalone binary.

#### Option B — Docker 

If Docker is installed, start Qdrant with:

```bash
docker compose up -d
```

### 2.Set up Python

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the API

```bash
uvicorn apps.backend.main:app --reload
```
Open http://localhost:8000/docs for the interactive API.

### 4. Health Check

Open http://localhost:8000/docs and try out GET/ to check status.


## 5. Try the loop (no AWS needed)

```bash
# Store a project decision
curl -X POST localhost:8000/ingest -H 'Content-Type: application/json' -d '{
  "text": "We chose the repository pattern for all DB access so business logic stays decoupled from the ORM. Rejected active-record because it leaks DB concerns into services.",
  "project": "demo", "source": "brainstorm", "title": "DB access decision"
}'

# Retrieve it semantically
curl -X POST localhost:8000/search -H 'Content-Type: application/json' -d '{
  "query": "how do we handle database access?", "project": "demo"
}'
```

You'll get the decision back, ranked by relevance. That's the core working.

---

## Turn on brainstorming (Bedrock)

1. In the AWS console → Bedrock → **Model access**, enable a Claude model.
2. Put the model id + region in `.env`.
3. Make sure your machine/EC2 has AWS creds (`aws configure` or an instance role).
4. Call `/chat` to brainstorm with context, then `/finalize` to export a prompt.

---

## Next steps (in order — don't boil the ocean)

1. **GitHub ingestion** — pull a repo's docs/README into `/ingest`.
2. **A minimal web UI** — a chat box that calls `/chat` and a "Finalize" button.
3. **Source provenance in the UI** — show which chunks were retrieved.
4. **Jira + Slack ingestion** — once GitHub end-to-end feels good.
5. **Shared knowledge bases** — multi-user project scoping (your team-sharing moat).

Ship #1 and #2 before anything else.

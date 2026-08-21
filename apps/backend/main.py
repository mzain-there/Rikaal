"""
Rikaal API — the pre-flight knowledge layer for code agents.

Endpoints:
  POST /ingest           store project knowledge (docs, decisions, notes)
  POST /ingest/github    ingest README.md and docs/ from a public GitHub repo
  POST /search           retrieve the most relevant chunks (no LLM)
  POST /chat             brainstorm with retrieved project context (uses Bedrock)
  POST /finalize         turn a brainstorm into a structured prompt for a coding agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from .vectordb import ensure_collection, add_chunks, search as vsearch, delete_by_repo
from .ingest import chunk_text
from .github import get_repo_tree, get_file_content, select_markdown_files, is_file_too_large
from . import llm

app = FastAPI(title="Rikaal", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_collection()
    yield


app = FastAPI(
    title="Rikaal",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------- models ----------
class IngestReq(BaseModel):
    text: str
    project: str = "default"
    source: str = "manual"      # manual | github | jira | slack | brainstorm
    title: str | None = None

class GitHubIngestReq(BaseModel):
    repo: str
    branch: str = "main"
    project: str = "default"

class SearchReq(BaseModel):
    query: str
    project: str = "default"
    top_k: int = 5


class ChatReq(BaseModel):
    query: str
    project: str = "default"
    history: list[dict] = []    # [{"role": "user"/"assistant", "content": "..."}]
    top_k: int = 5


class FinalizeReq(BaseModel):
    history: list[dict]
    project: str = "default"


# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(req: IngestReq):
    chunks = chunk_text(req.text)
    meta = {"project": req.project, "source": req.source}
    if req.title:
        meta["title"] = req.title
    n = add_chunks(chunks, meta)
    return {"ingested_chunks": n, "project": req.project}

@app.post("/ingest/github")
def ingest_github(req: GitHubIngestReq):
    try:
        tree = get_repo_tree(req.repo, req.branch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    selected_files = select_markdown_files(tree)

    if not selected_files:
        raise HTTPException(
            status_code=400,
            detail="No README.md or Markdown files under docs/ were found in this repository.",
        )

    # Remove previous ingestion for this project/repository combination.
    delete_by_repo(req.project, req.repo)

    files = []
    skipped = []
    total_chunks = 0

    for file_info in selected_files:
        path = file_info["path"]
        size = file_info["size"]

        if is_file_too_large(size):
            skipped.append(
                {
                    "path": path,
                    "reason": "File is larger than 100 KB",
                }
            )
            continue

        try:
            text = get_file_content(req.repo, path, req.branch)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        chunks = chunk_text(text)

        metadata = {
            "source": "github",
            "project": req.project,
            "repo": req.repo,
            "path": path,
        }

        chunk_count = add_chunks(chunks, metadata)

        files.append(
            {
                "path": path,
                "chunks": chunk_count,
            }
        )

        total_chunks += chunk_count

    if not files:
        raise HTTPException(
            status_code=400,
            detail="All selected Markdown files were larger than 100 KB; nothing was ingested.",
        )

    return {
        "repo": req.repo,
        "files": files,
        "skipped": skipped,
        "total_chunks": total_chunks,
    }

@app.post("/search")
def search(req: SearchReq):
    return {"results": vsearch(req.query, top_k=req.top_k, project=req.project)}


@app.post("/chat")
def chat(req: ChatReq):
    hits = vsearch(req.query, top_k=req.top_k, project=req.project)
    context = "\n\n---\n\n".join(
        f"[{h['payload'].get('source','?')}] {h['text']}" for h in hits
    ) or "(no project knowledge retrieved yet)"

    system = (
        "You are Rikaal, a brainstorming partner that knows this software project. "
        "Use the retrieved project context below to help the user think through "
        "features and decisions. Be concrete. If the context is missing something, "
        "say so rather than inventing it.\n\n"
        f"=== PROJECT CONTEXT ===\n{context}\n=== END CONTEXT ==="
    )
    messages = req.history + [{"role": "user", "content": req.query}]
    answer = llm.complete(system, messages)
    return {"answer": answer, "used_context": [h["text"] for h in hits]}


@app.post("/finalize")
def finalize(req: FinalizeReq):
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in req.history)
    system = (
        "You convert a brainstorming conversation into a single, tightly-scoped "
        "prompt that a coding agent (Claude Code, Cursor, etc.) can execute without "
        "further clarification. Output ONLY the final prompt, structured as:\n"
        "## Goal\n## Context\n## Constraints\n## Acceptance Criteria\n## Out of Scope"
    )
    messages = [{"role": "user", "content": f"Brainstorm transcript:\n\n{convo}"}]
    prompt = llm.complete(system, messages, max_tokens=1200)
    return {"structured_prompt": prompt}

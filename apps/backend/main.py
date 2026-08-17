"""
Rikaal API — the pre-flight knowledge layer for code agents.

Endpoints:
  POST /ingest    store project knowledge (docs, decisions, notes)
  POST /search    retrieve the most relevant chunks (no LLM)
  POST /chat      brainstorm with retrieved project context (uses Bedrock)
  POST /finalize  turn a brainstorm into a structured prompt for a coding agent
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .vectordb import ensure_collection, add_chunks, search as vsearch
from .ingest import chunk_text
from . import llm

app = FastAPI(title="Rikaal", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def _startup():
    ensure_collection()


# ---------- models ----------
class IngestReq(BaseModel):
    text: str
    project: str = "default"
    source: str = "manual"      # manual | github | jira | slack | brainstorm
    title: str | None = None


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

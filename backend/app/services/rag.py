"""
RAG pipeline for business knowledge (policies, service details, FAQ).

Flow:
  markdown files in app/knowledge_base/
    -> RecursiveCharacterTextSplitter (LangChain)
    -> embeddings (see embeddings.py)
    -> vector store (FAISS locally-persisted, or pgvector in production)
    -> similarity_search at query time, injected into the agent as a tool

Why RAG here at all, for a booking assistant: policy questions ("can I
cancel for free?", "do I need a deposit?", "is your place wheelchair
accessible?") are exactly the kind of thing that's easy for an LLM to
confidently hallucinate about a specific business. Grounding those answers
in actual source documents — and being able to point back to which document
answered — is the difference between a demo and something you'd trust in
production.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.embeddings import embeddings_fingerprint, get_embeddings

settings = get_settings()

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"
INDEX_DIR = Path(__file__).resolve().parents[2] / settings.faiss_index_dir


def _load_source_documents() -> list[Document]:
    docs = []
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": path.stem}))
    return docs


def _chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)


def _fingerprint_path() -> Path:
    return INDEX_DIR / ".fingerprint"


def _index_is_stale() -> bool:
    fp_path = _fingerprint_path()
    if not fp_path.exists():
        return True
    return fp_path.read_text().strip() != embeddings_fingerprint()


def build_index(force: bool = False) -> int:
    """Builds (or rebuilds) the vector index from the knowledge base docs,
    using whichever backend is configured. Returns the number of chunks
    indexed, or -1 if an up-to-date FAISS index already existed and force
    was not requested (pgvector has no cheap staleness check, so it always
    re-embeds and upserts — Postgres handles the dedup via collection reset)."""
    if settings.vector_store_backend == "pgvector":
        return _build_index_pgvector()
    return _build_index_faiss(force=force)


def _build_index_faiss(force: bool = False) -> int:
    from langchain_community.vectorstores import FAISS

    if not force and INDEX_DIR.exists() and not _index_is_stale():
        return -1  # already up to date

    docs = _load_source_documents()
    chunks = _chunk_documents(docs)
    embeddings = get_embeddings()

    vector_store = FAISS.from_documents(chunks, embeddings)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(INDEX_DIR))
    _fingerprint_path().write_text(embeddings_fingerprint())
    _get_faiss_store.cache_clear()
    return len(chunks)


def _build_index_pgvector() -> int:
    docs = _load_source_documents()
    chunks = _chunk_documents(docs)
    store = _get_pgvector_store()
    # PGVector.add_documents upserts into the named collection; we clear
    # first so re-running the build doesn't accumulate duplicate chunks
    # across repeated deploys.
    store.delete_collection()
    store.create_collection()
    store.add_documents(chunks)
    return len(chunks)


@lru_cache
def _get_faiss_store():
    from langchain_community.vectorstores import FAISS

    if not INDEX_DIR.exists() or _index_is_stale():
        build_index(force=True)

    embeddings = get_embeddings()
    return FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )


def _get_pgvector_store():
    from langchain_postgres import PGVector

    embeddings = get_embeddings()
    # langchain-postgres expects a psycopg (v3) URL; the app's main
    # DATABASE_URL uses the psycopg2 driver for the rest of the ORM, so we
    # swap the driver segment here rather than requiring two separate env vars.
    conn_str = settings.database_url.replace("postgresql+psycopg2", "postgresql+psycopg")
    store = PGVector(
        embeddings=embeddings,
        collection_name="business_knowledge",
        connection=conn_str,
        use_jsonb=True,
    )
    return store


def get_vector_store():
    if settings.vector_store_backend == "pgvector":
        return _get_pgvector_store()
    return _get_faiss_store()


def retrieve(query: str, k: int | None = None) -> list[dict]:
    """Returns the top-k chunks relevant to `query`, each with its source
    document name and text — used both by the AI agent tool and directly
    testable without any LLM in the loop."""
    k = k or settings.rag_top_k
    store = get_vector_store()
    results = store.similarity_search_with_score(query, k=k)
    return [
        {
            "source": doc.metadata.get("source", "unknown"),
            "text": doc.page_content,
            "score": float(score),
        }
        for doc, score in results
    ]


def format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no relevant information found in the knowledge base)"
    parts = []
    for c in chunks:
        parts.append(f"[Source: {c['source']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)

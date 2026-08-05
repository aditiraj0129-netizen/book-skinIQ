from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import admin, auth, availability, business, chat, services

settings = get_settings()

app = FastAPI(
    title="Appointment Booking AI",
    description="Chat-based appointment booking assistant with an admin dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(services.router)
app.include_router(availability.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(business.router)


@app.on_event("startup")
def _ensure_rag_index():
    """Builds the RAG vector index on first boot (or if the embeddings
    config changed since it was last built). Only applies to the local
    FAISS backend — a pgvector backend is expected to be indexed via the
    explicit `python -m app.build_rag_index` command as part of deployment,
    since it's a shared store rather than a per-instance file."""
    if settings.vector_store_backend == "faiss":
        from app.services import rag

        rag.build_index()  # no-op if already up to date


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_engine": "grok" if settings.xai_api_key else "fallback"}

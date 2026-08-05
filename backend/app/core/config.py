"""
Centralized app configuration.

All environment-driven values live here so the rest of the codebase never
touches os.environ directly. This also makes it trivial to see, in one file,
every external dependency the system has (DB, Claude API, auth secret, etc).
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/appointments"

    # --- Auth ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    admin_username: str = "admin"
    admin_password: str = "admin123"  # overridden via env in real deployments

    # --- Grok / xAI ---
    xai_api_key: Optional[str] = None
    xai_model: str = "grok-4"
    xai_base_url: str = "https://api.x.ai/v1"
    # If no API key is present, the NLU service transparently falls back to
    # a deterministic rule-based parser (see services/nlu_fallback.py).
    # This keeps the whole app runnable in CI / for reviewers without a key.

    # --- RAG / embeddings / vector store ---
    # xAI does not currently expose a public embeddings endpoint, so
    # embeddings are handled separately from the chat model. If
    # OPENAI_API_KEY is set, real neural embeddings (text-embedding-3-small)
    # are used for the best retrieval quality. Otherwise the app falls back
    # to a deterministic, fully local hashing-based embedder (see
    # services/embeddings.py) so RAG still works with zero external calls.
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 512

    # "faiss" = local, file-persisted vector index (default; zero extra infra).
    # "pgvector" = production backend using the Postgres pgvector extension,
    # reusing the same database as the rest of the app.
    vector_store_backend: str = "faiss"
    faiss_index_dir: str = "data/faiss_index"
    rag_top_k: int = 4

    # --- Business rules ---
    business_timezone: str = "Asia/Kolkata"
    business_open_hour: int = 9   # 9 AM
    business_close_hour: int = 18  # 6 PM
    slot_duration_minutes: int = 30
    booking_horizon_days: int = 30  # how far ahead users can book

    # --- CORS ---
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()

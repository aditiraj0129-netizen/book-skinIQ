"""
Embedding backends for the RAG pipeline.

xAI (Grok) does not currently expose a public embeddings endpoint, so we
decouple "which model answers chat" from "which model embeds text for
retrieval." Two backends are available:

- LocalHashingEmbeddings: a fully offline, deterministic embedder built on
  scikit-learn's feature hashing (HashingVectorizer + TF-IDF re-weighting).
  It needs no API key and no model download, so RAG works end-to-end with
  zero external dependencies. It captures lexical/keyword-level similarity
  well (good enough for FAQ-style retrieval over a small, curated knowledge
  base) but doesn't understand synonyms or paraphrasing the way a neural
  embedding model would.
- OpenAIEmbeddings (text-embedding-3-small): used automatically when
  OPENAI_API_KEY is set, for real semantic embeddings.

get_embeddings() picks whichever is configured, mirroring the same
graceful-degradation pattern used for the chat model itself.
"""
from __future__ import annotations

import hashlib

import numpy as np
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import HashingVectorizer

from app.core.config import get_settings

settings = get_settings()


class LocalHashingEmbeddings(Embeddings):
    """Deterministic, offline embeddings via the hashing trick.

    Fitting a TF-IDF transformer per-call would break the "embeddings are
    just a pure function of the text" contract that vector stores rely on
    (a document embedded today must match one embedded next week). To keep
    embeddings stable across calls without maintaining global IDF state, we
    use sublinear term-frequency scaling on the hashed features instead of
    corpus-dependent IDF — a standard trick for streaming/stateless hashing
    vectorizers.
    """

    def __init__(self, n_features: int = 512):
        self.n_features = n_features
        self._vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            norm=None,
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        matrix = self._vectorizer.transform(texts)
        dense = matrix.toarray().astype(np.float64)
        # Sublinear term-frequency scaling (log1p), applied manually since
        # HashingVectorizer has no built-in IDF/sublinear-tf option (IDF
        # would require corpus-wide state, which we deliberately avoid to
        # keep embeddings a pure function of a single text).
        dense = np.log1p(dense)
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = dense / norms
        return normalized.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


def get_embeddings() -> Embeddings:
    if settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
            dimensions=settings.embedding_dimensions,
        )
    return LocalHashingEmbeddings(n_features=settings.embedding_dimensions)


def embeddings_fingerprint() -> str:
    """A short string identifying which embedding backend/config is active,
    used to detect a stale on-disk index (e.g. built with the local hasher,
    then the app reconfigured to use OpenAI embeddings)."""
    if settings.openai_api_key:
        raw = f"openai:{settings.embedding_model}:{settings.embedding_dimensions}"
    else:
        raw = f"local-hash:{settings.embedding_dimensions}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

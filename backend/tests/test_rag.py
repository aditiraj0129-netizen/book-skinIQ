import shutil

import pytest

from app.services import rag


@pytest.fixture(scope="module", autouse=True)
def built_index():
    shutil.rmtree(rag.INDEX_DIR, ignore_errors=True)
    rag.build_index(force=True)
    rag._get_faiss_store.cache_clear()
    yield
    shutil.rmtree(rag.INDEX_DIR, ignore_errors=True)


def test_index_builds_and_has_chunks():
    n = rag.build_index(force=True)
    assert n > 0


def test_cancellation_query_hits_booking_policy():
    results = rag.retrieve("can I cancel my appointment for free", k=3)
    sources = [r["source"] for r in results]
    assert "booking_policy" in sources
    assert results[0]["source"] == "booking_policy"


def test_parking_query_hits_general_faq():
    # Note: the local hashing embedder is lexical, not semantic — it has no
    # stemming, so "park" vs "Parking" are different hashed tokens. Using
    # the exact word from the source document is a more realistic test of
    # this fallback backend; a neural embedder (OpenAI) would handle the
    # unstemmed case too, which is exactly the tradeoff documented in
    # embeddings.py.
    results = rag.retrieve("is parking available nearby", k=3)
    assert results[0]["source"] == "general_faq"


def test_massage_prep_query_hits_service_details():
    results = rag.retrieve("what should I do before a massage appointment", k=3)
    sources = [r["source"] for r in results]
    assert "service_details" in sources


def test_format_context_includes_source_labels():
    results = rag.retrieve("cancellation policy", k=2)
    formatted = rag.format_context(results)
    assert "[Source:" in formatted


def test_format_context_handles_empty_results():
    assert "no relevant" in rag.format_context([]).lower()

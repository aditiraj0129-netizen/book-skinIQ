"""
Explicitly (re)builds the RAG vector index from app/knowledge_base/*.md.

Usage:
    python -m app.build_rag_index          # build if stale/missing
    python -m app.build_rag_index --force  # always rebuild

For the faiss backend this is optional (the app auto-builds a stale/missing
index on startup — see main.py). For the pgvector backend this is the
command you run as part of deployment, since a shared Postgres-backed index
shouldn't be silently rebuilt by every app instance on every boot.
"""
import argparse

from app.services import rag


def main():
    parser = argparse.ArgumentParser(description="Build/rebuild the RAG vector index.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already up to date.")
    args = parser.parse_args()

    n = rag.build_index(force=args.force)
    if n == -1:
        print("Index already up to date — nothing to do (use --force to rebuild anyway).")
    else:
        print(f"Indexed {n} chunks from {rag.KNOWLEDGE_BASE_DIR}")


if __name__ == "__main__":
    main()

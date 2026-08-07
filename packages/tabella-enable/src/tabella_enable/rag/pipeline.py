"""The vectorization pipeline: records -> chunks -> embeddings -> vector store.

Produces the RAG index manifest entry per asset (spec/ai-artifact-manifest.md,
part 2). Idempotent: re-running replaces the asset's collection.
"""

from __future__ import annotations

from typing import Any

from tabella_core.connectors import get_connector
from tabella_core.interfaces import EmbeddingProvider, VectorStore
from tabella_core.models import TABELLA_SPEC_VERSION, AssetDescriptor

from tabella_enable.rag.chunking import chunk_text

_PAGE_SIZE = 500


def collection_name(descriptor: AssetDescriptor) -> str:
    return f"tabella_{descriptor.id.replace('.', '_')}"


def _record_ref(descriptor: AssetDescriptor, record: dict, index: int) -> str:
    pk = descriptor.asset_schema.primary_key
    if pk:
        return ",".join(str(record.get(k)) for k in pk)
    return str(index)


def vectorize_asset(
    descriptor: AssetDescriptor,
    embedder: EmbeddingProvider,
    store: VectorStore,
) -> dict[str, Any]:
    """Vectorize one asset per its profile; returns its rag.json index entry."""
    profile = descriptor.enablement.vectorization
    if not profile.enabled:
        raise ValueError(f"Asset '{descriptor.id}' has vectorization disabled")
    content_fields = profile.content_fields or [
        f.name for f in descriptor.asset_schema.fields if f.type.value == "string"
    ]

    connector = get_connector(descriptor.source.connector)
    chunks: list[dict] = []
    offset = 0
    while True:
        records, _total = connector.fetch(descriptor, limit=_PAGE_SIZE, offset=offset)
        for index, record in enumerate(records):
            text = "\n".join(
                str(record[f]) for f in content_fields if record.get(f) is not None
            )
            ref = _record_ref(descriptor, record, offset + index)
            metadata = {f: record.get(f) for f in profile.metadata_fields}
            for chunk_index, piece in enumerate(
                chunk_text(text, profile.chunking, profile.chunk_size)
            ):
                chunks.append(
                    {
                        "id": f"{descriptor.id}:{ref}:{chunk_index}",
                        "record_ref": ref,
                        "content": piece,
                        "metadata": metadata,
                    }
                )
        if len(records) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    embeddings = embedder.embed([c["content"] for c in chunks]) if chunks else []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        chunk["embedding"] = embedding
    dimensions = len(embeddings[0]) if embeddings else embedder.dimensions

    collection = collection_name(descriptor)
    store.replace_collection(collection, chunks, dimensions)

    return {
        "asset": descriptor.id,
        "content_fields": content_fields,
        "chunking": {
            "strategy": profile.chunking.value,
            "chunk_size": profile.chunk_size,
        },
        "embedding": {"model": embedder.model, "dimensions": dimensions},
        "store": {"backend": store.name, "collection": collection},
        "metadata_fields": profile.metadata_fields,
        "search_endpoint": {"method": "POST", "path": f"/assets/{descriptor.id}/search"},
        "chunk_count": len(chunks),
    }


def build_rag_manifest(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tabella_version": TABELLA_SPEC_VERSION, "indexes": entries}

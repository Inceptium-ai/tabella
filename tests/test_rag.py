"""End-to-end RAG tests: chunking, embeddings, local store, pipeline, search,
REST search endpoint, and MCP tool listing/dispatch — all offline (hash
embeddings + local store)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from tabella_core.models import (
    AssetMeta,
    ChunkingStrategy,
    EnablementProfile,
    OnboardingManifest,
    SourceRef,
    VectorizationProfile,
)
from tabella_core.pipeline import register
from tabella_core.store import load_catalog
from tabella_enable.mcp_server import call_catalog_tool, catalog_tools
from tabella_enable.rag import SearchService
from tabella_enable.rag.chunking import chunk_text
from tabella_enable.rag.embeddings import HashEmbeddings
from tabella_enable.rag.pipeline import build_rag_manifest, vectorize_asset
from tabella_enable.rag.store import LocalVectorStore
from tabella_enable.rest import build_app
from tabella_enable.tools import build_manifest

TICKETS = [
    (1, "Package arrived damaged", "The box was crushed and the mug is chipped."),
    (2, "Cannot reset my password", "The password reset email never arrives."),
    (3, "Invoice VAT question", "The invoice is missing the German VAT breakdown."),
]


@pytest.fixture
def tickets_descriptor(tmp_path):
    db = tmp_path / "support.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE tickets (id INTEGER PRIMARY KEY, subject TEXT NOT NULL,"
            " body TEXT NOT NULL)"
        )
        conn.executemany("INSERT INTO tickets VALUES (?, ?, ?)", TICKETS)
    manifest = OnboardingManifest(
        asset=AssetMeta(name="tickets", domain="support"),
        source=SourceRef(
            connector="sqlite", name="support", uri=f"sqlite:///{db}", native_name="tickets"
        ),
        enablement=EnablementProfile(
            vectorization=VectorizationProfile(
                enabled=True,
                content_fields=["subject", "body"],
                metadata_fields=["id"],
                chunking=ChunkingStrategy.document,
            )
        ),
    )
    return register(manifest, tmp_path / "catalog").descriptor


@pytest.fixture
def rag(tmp_path, tickets_descriptor):
    embedder = HashEmbeddings(dimensions=64)
    store = LocalVectorStore(tmp_path / "vectors")
    entry = vectorize_asset(tickets_descriptor, embedder, store)
    return tickets_descriptor, SearchService(embedder, store), entry


def test_chunking_strategies():
    text = "First sentence here. Second sentence follows. Third one ends it."
    assert chunk_text(text, ChunkingStrategy.document, 10) == [text]
    fixed = chunk_text("a" * 250, ChunkingStrategy.fixed, 100)
    assert len(fixed) >= 3 and all(len(c) <= 100 for c in fixed)
    semantic = chunk_text(text, ChunkingStrategy.semantic, 45)
    assert len(semantic) > 1 and all(len(c) <= 45 for c in semantic)
    assert all(c.endswith(".") for c in semantic)  # splits on sentence boundaries
    assert chunk_text("   ", ChunkingStrategy.fixed, 100) == []


def test_hash_embeddings_deterministic_and_normalized():
    e = HashEmbeddings(dimensions=32)
    a1, a2 = e.embed(["password reset email"]), e.embed(["password reset email"])
    assert a1 == a2
    norm = sum(v * v for v in a1[0])
    assert abs(norm - 1.0) < 1e-9


def test_vectorize_produces_manifest_entry(rag):
    descriptor, _, entry = rag
    assert entry["asset"] == "support.tickets"
    assert entry["chunk_count"] == 3
    assert entry["store"] == {"backend": "local", "collection": "tabella_support_tickets"}
    assert entry["embedding"]["dimensions"] == 64
    manifest = build_rag_manifest([entry])
    assert manifest["indexes"][0]["search_endpoint"]["path"] == "/assets/support.tickets/search"


def test_search_returns_relevant_chunk_with_citation(rag):
    descriptor, service, _ = rag
    results = service.search(descriptor, "password reset email never arrives", top_k=2)
    assert results[0]["metadata"] == {"id": 2}
    assert results[0]["record_ref"] == "2"
    assert "password" in results[0]["content"].lower()
    assert results[0]["score"] > results[1]["score"]
    assert "embedding" not in results[0]


def test_revectorize_replaces_collection(rag, tmp_path):
    descriptor, service, _ = rag
    embedder = HashEmbeddings(dimensions=64)
    store = LocalVectorStore(tmp_path / "vectors")
    entry = vectorize_asset(descriptor, embedder, store)
    assert entry["chunk_count"] == 3  # replaced, not appended


def test_rest_search_endpoint(rag, tmp_path):
    descriptor, service, _ = rag
    client = TestClient(build_app(load_catalog(tmp_path / "catalog"), search=service))
    resp = client.post(
        "/assets/support.tickets/search", json={"query": "damaged package", "top_k": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0]["metadata"]["id"] == 1
    # not vectorized / not configured error paths
    assert client.post("/assets/support.tickets/search", json={}).status_code == 400
    bare = TestClient(build_app(load_catalog(tmp_path / "catalog")))
    assert bare.post(
        "/assets/support.tickets/search", json={"query": "x"}
    ).status_code == 503


def test_tools_manifest_includes_search_tool(rag):
    descriptor, _, _ = rag
    names = {t["name"] for t in build_manifest([descriptor])["tools"]}
    assert names == {"query_support_tickets", "search_support_tickets"}


def test_mcp_tools_and_dispatch(rag):
    descriptor, service, _ = rag
    tools = catalog_tools([descriptor], with_search=True)
    assert {t["name"] for t in tools} == {"query_support_tickets", "search_support_tickets"}

    result = call_catalog_tool([descriptor], "query_support_tickets", {"id": 3})
    assert result["data"][0]["subject"] == "Invoice VAT question"

    result = call_catalog_tool(
        [descriptor], "search_support_tickets", {"query": "VAT invoice"}, search=service
    )
    assert result["data"][0]["metadata"]["id"] == 3

    with pytest.raises(KeyError):
        call_catalog_tool([descriptor], "nope", {})
    # search tools are hidden when no search service is configured
    assert not any(
        t["name"].startswith("search_")
        for t in catalog_tools([descriptor], with_search=False)
    )

"""Embedding providers.

- `hash` — deterministic, offline, dependency-free: token-hash bag-of-words
  vectors. Not semantically meaningful, but stable and cheap; the dev/test
  default so the whole RAG path runs with no API key or model server.
- `openai` — any OpenAI-compatible /v1/embeddings endpoint (OpenAI, LiteLLM,
  Ollama, vLLM...). Configure via TABELLA_EMBED_* env vars.
"""

from __future__ import annotations

import hashlib
import math
import os
import re

from tabella_core.interfaces import EmbeddingProvider

_TOKEN = re.compile(r"[a-z0-9]+")


class HashEmbeddings(EmbeddingProvider):
    name = "hash"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        self.model = f"tabella-hash-{dimensions}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class OpenAICompatibleEmbeddings(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_url = (
            api_url or os.environ.get("TABELLA_EMBED_API_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("TABELLA_EMBED_API_KEY", "")
        self.model = model or os.environ.get("TABELLA_EMBED_MODEL", "text-embedding-3-small")
        self.dimensions = 0  # discovered from the first response

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx  # lazy: hash provider needs no HTTP stack

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = httpx.post(
            f"{self.api_url}/embeddings",
            json={"model": self.model, "input": texts},
            headers=headers,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        vectors = [d["embedding"] for d in data]
        if vectors:
            self.dimensions = len(vectors[0])
        return vectors


def embedding_provider_from_env() -> EmbeddingProvider:
    provider = os.environ.get("TABELLA_EMBED_PROVIDER", "hash")
    if provider == "openai":
        return OpenAICompatibleEmbeddings()
    if provider == "hash":
        return HashEmbeddings(int(os.environ.get("TABELLA_EMBED_DIM", "256")))
    raise ValueError(f"Unknown TABELLA_EMBED_PROVIDER: {provider!r} (hash|openai)")

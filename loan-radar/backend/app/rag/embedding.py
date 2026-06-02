from __future__ import annotations

import json
import logging
from typing import Any

import requests

from app.models import ModelConfig

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, *, model_config: ModelConfig, api_key: str) -> None:
        self._model_config = model_config
        self._api_key = api_key

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            return []

        endpoint = f"{self._model_config.base_url.rstrip('/')}/embeddings"
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model_config.model_name,
                    "input": text[:8000],
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()

            embedding = payload["data"][0]["embedding"]
            return embedding
        except Exception as exc:
            logger.error("Embedding request failed: %s", exc)
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        endpoint = f"{self._model_config.base_url.rstrip('/')}/embeddings"
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model_config.model_name,
                    "input": [t[:8000] for t in texts],
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()

            results = [None] * len(texts)
            for item in payload["data"]:
                results[item["index"]] = item["embedding"]

            return [r for r in results if r is not None]
        except Exception as exc:
            logger.error("Batch embedding request failed: %s", exc)
            raise

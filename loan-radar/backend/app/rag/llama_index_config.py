from __future__ import annotations

import logging
from typing import Any

from llama_index.core import Settings as LlamaSettings
from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai import OpenAIEmbedding

from app.models import ModelConfig

logger = logging.getLogger(__name__)

_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "tongyi": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "default_embed_model": "text-embedding-v3",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-plus",
        "default_embed_model": "embedding-3",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "default_embed_model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "default_embed_model": "text-embedding-3-small",
    },
}


def build_llm(
    *,
    model_config: ModelConfig,
    api_key: str,
) -> LLM:
    provider = (model_config.provider or "openai").lower()
    preset = _PROVIDER_PRESETS.get(provider, {})

    base_url = model_config.base_url or preset.get("base_url", "")
    model_name = model_config.model_name or preset.get("default_model", "gpt-4o")

    llm = OpenAILike(
        model=model_name,
        api_key=api_key,
        api_base=base_url,
        is_chat_model=True,
        temperature=0.7,
        max_tokens=2048,
    )

    logger.info("Built LLM: provider=%s, model=%s, base_url=%s", provider, model_name, base_url)
    return llm


def build_embed_model(
    *,
    model_config: ModelConfig,
    api_key: str,
) -> BaseEmbedding:
    provider = (model_config.provider or "openai").lower()
    preset = _PROVIDER_PRESETS.get(provider, {})

    base_url = model_config.base_url or preset.get("base_url", "")
    embed_model_name = model_config.model_name or preset.get("default_embed_model", "text-embedding-3-small")

    embed_model = OpenAIEmbedding(
        model=embed_model_name,
        api_key=api_key,
        api_base=base_url,
    )

    logger.info("Built Embedding: provider=%s, model=%s", provider, embed_model_name)
    return embed_model


def configure_llama_settings(
    *,
    llm: LLM | None = None,
    embed_model: BaseEmbedding | None = None,
) -> None:
    if llm is not None:
        LlamaSettings.llm = llm
    if embed_model is not None:
        LlamaSettings.embed_model = embed_model

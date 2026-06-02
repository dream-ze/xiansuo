from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.models import ModelConfig
from app.services.ai_service import OpenAICompatibleTextClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_STRUCTURED_SYSTEM_SUFFIX = (
    "\n\n重要：你必须返回严格的 JSON 对象，不要返回任何其他文本、markdown 代码块或解释。"
    "JSON 必须符合提供的 schema。"
)

_PARSE_RETRY_PREFIX = (
    "你上次的返回无法解析为有效的 JSON。错误信息：{error}\n"
    "请严格按照 schema 返回 JSON，不要添加任何额外文本：\n"
)


class StructuredLLMClient:
    def __init__(self, text_client: OpenAICompatibleTextClient | None = None) -> None:
        self._text_client = text_client or OpenAICompatibleTextClient()

    def complete_structured(
        self,
        *,
        model_config: ModelConfig,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        max_retries: int = 2,
        temperature: float = 0.3,
    ) -> tuple[T, dict[str, Any]]:
        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

        enriched_system = (
            system_prompt
            + _STRUCTURED_SYSTEM_SUFFIX
            + f"\n\n返回 JSON 的 schema 如下：\n```json\n{schema_str}\n```"
        )

        last_error: Exception | None = None
        current_user_prompt = user_prompt

        for attempt in range(max_retries + 1):
            try:
                raw_content = self._text_client._complete(
                    model_config=model_config,
                    api_key=api_key,
                    system_prompt=enriched_system,
                    user_prompt=current_user_prompt,
                    temperature=temperature,
                )

                parsed_json = self._extract_json(raw_content)
                result = response_model.model_validate(parsed_json)

                metadata = {
                    "attempts": attempt + 1,
                    "raw_content_length": len(raw_content),
                    "model": model_config.model_name,
                }
                return result, metadata

            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Structured LLM parse failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    str(exc)[:300],
                )
                current_user_prompt = (
                    _PARSE_RETRY_PREFIX.format(error=str(exc)[:200])
                    + user_prompt
                )

        raise ValueError(
            f"Structured LLM failed after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        stripped = raw.strip()

        if stripped.startswith("```"):
            lines = stripped.split("\n")
            json_lines: list[str] = []
            inside = False
            for line in lines:
                if line.strip().startswith("```"):
                    if inside:
                        break
                    inside = True
                    continue
                if inside:
                    json_lines.append(line)
            stripped = "\n".join(json_lines).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        return json.loads(raw)

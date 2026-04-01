from __future__ import annotations

import importlib
import json
import logging
from typing import Any

from app.core.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, skill_name: str) -> None:
        self.skill_name = skill_name

    def generate_json(
        self,
        *,
        instruction_text: str,
        response_schema: dict[str, Any],
        customer_payload: dict[str, Any],
        temperature: float,
        external_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        try:
            openai_module = importlib.import_module("openai")
            openai_client_cls = getattr(openai_module, "OpenAI")
            client_kwargs = self._build_client_kwargs()
            if client_kwargs is None:
                return None

            client = openai_client_cls(**client_kwargs)
            model_name = settings.LLM_MODEL or settings.OPENAI_MODEL

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": instruction_text},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "customer": customer_payload,
                                "required_schema": response_schema,
                                "external_context": external_context or {},
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=temperature,
                max_tokens=512,
            )

            text_output = response.choices[0].message.content if response.choices else None
            parsed_output = self._parse_json_output(text_output)
            if parsed_output is None:
                return None

            # Preserve model identity so downstream can mark whether result came from LLM.
            parsed_output["_model_version"] = str(getattr(response, "model", model_name))
            return parsed_output
        except Exception as exc:
            logger.warning("%s LLM call failed, fallback to rules: %s", self.skill_name, exc)
            return None

    def _build_client_kwargs(self) -> dict[str, Any] | None:
        provider = settings.LLM_PROVIDER.lower().strip()
        base_url = (settings.LLM_BASE_URL or "").strip() or None

        kwargs: dict[str, Any] = {
            "timeout": settings.LLM_REQUEST_TIMEOUT,
            "max_retries": settings.LLM_MAX_RETRIES,
        }

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                return None
            kwargs["api_key"] = settings.OPENAI_API_KEY
            if base_url:
                kwargs["base_url"] = base_url
            return kwargs

        if provider == "local":
            kwargs["base_url"] = base_url or "http://localhost:11434/v1"
            kwargs["api_key"] = settings.LLM_API_KEY or settings.OPENAI_API_KEY or "local-dev-key"
            return kwargs

        if provider == "auto":
            if base_url:
                kwargs["base_url"] = base_url
                kwargs["api_key"] = settings.LLM_API_KEY or settings.OPENAI_API_KEY or "local-dev-key"
                return kwargs
            if settings.OPENAI_API_KEY:
                kwargs["api_key"] = settings.OPENAI_API_KEY
                return kwargs
            return None

        logger.warning("Unsupported LLM_PROVIDER='%s'. Expected local, openai, or auto.", provider)
        return None

    def _parse_json_output(self, text_output: Any) -> dict[str, Any] | None:
        if isinstance(text_output, list):
            text_output = "\n".join(str(item) for item in text_output)
        if not isinstance(text_output, str):
            return None

        cleaned = text_output.strip()
        if not cleaned:
            return None

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(cleaned[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

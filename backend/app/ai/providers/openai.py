"""
OpenAI chat completions provider (HTTP via httpx).
"""

import time
from typing import Any, Dict, Optional

import httpx

from app.ai.base.provider import BaseAIProvider
from app.ai.base.types import (
    AIHealth,
    AIProviderMetadata,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    TokenUsage,
)
from app.ai.exceptions import AICredentialError, AIGenerationError
from app.connectors.credentials.models import ConnectorCredentials

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseAIProvider):
    """OpenAI Chat Completions API client."""

    def __init__(
        self,
        credentials: Optional[ConnectorCredentials] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        **dependencies: Any,
    ) -> None:
        super().__init__(
            credentials=credentials,
            api_key=api_key,
            base_url=base_url or DEFAULT_BASE_URL,
            timeout=timeout,
            **dependencies,
        )

    def metadata(self) -> AIProviderMetadata:
        return AIProviderMetadata(
            name="openai",
            display_name="OpenAI",
            version="1.0.0",
            description="OpenAI Chat Completions API",
            homepage="https://platform.openai.com/docs",
            default_model=DEFAULT_MODEL,
            supported_models=["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
            capabilities=["generate", "health_check", "chat"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        api_key = self.require_api_key()
        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in request.messages
            ],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop"] = request.stop

        data = await self._post_json("/chat/completions", api_key, payload)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"] or ""
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            raise AIGenerationError(
                "Unexpected OpenAI response shape",
                details={"provider": "openai", "raw_keys": list(data.keys())},
            ) from exc

        usage_raw = data.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=usage_raw.get("prompt_tokens"),
            completion_tokens=usage_raw.get("completion_tokens"),
            total_tokens=usage_raw.get("total_tokens"),
        )
        return GenerateResponse(
            content=content,
            model=data.get("model", request.model),
            provider="openai",
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
        )

    async def health_check(self) -> AIHealth:
        started = time.perf_counter()
        try:
            api_key = self.require_api_key()
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=min(self.timeout, 15.0),
            ) as client:
                response = await client.get("/models")
                latency = (time.perf_counter() - started) * 1000
                if response.status_code == 401:
                    return AIHealth(
                        status=HealthStatus.UNHEALTHY,
                        provider="openai",
                        latency_ms=latency,
                        message="Invalid OpenAI API key",
                        details={"status_code": response.status_code},
                    )
                if response.status_code >= 400:
                    return AIHealth(
                        status=HealthStatus.DEGRADED,
                        provider="openai",
                        latency_ms=latency,
                        message=f"OpenAI health probe failed ({response.status_code})",
                        details={"status_code": response.status_code},
                    )
                return AIHealth(
                    status=HealthStatus.HEALTHY,
                    provider="openai",
                    latency_ms=latency,
                    message="ok",
                )
        except AICredentialError as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="openai",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=str(exc),
            )
        except Exception as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="openai",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=f"OpenAI health check error: {exc}",
            )

    async def _post_json(
        self, path: str, api_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        assert self.base_url is not None
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            ) as client:
                response = await client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise AIGenerationError(
                f"OpenAI HTTP error: {exc}",
                details={"provider": "openai"},
            ) from exc

        if response.status_code == 401:
            raise AIGenerationError(
                "OpenAI authentication failed — check AI_OPENAI_API_KEY",
                details={"provider": "openai", "status_code": 401},
            )
        if response.status_code >= 400:
            raise AIGenerationError(
                f"OpenAI API error ({response.status_code}): {response.text[:500]}",
                details={"provider": "openai", "status_code": response.status_code},
            )
        data = response.json()
        if not isinstance(data, dict):
            raise AIGenerationError(
                "OpenAI returned a non-object JSON body",
                details={"provider": "openai"},
            )
        return data

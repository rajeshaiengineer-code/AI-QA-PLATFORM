"""
Anthropic Claude Messages API provider (HTTP via httpx).
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.ai.base.provider import BaseAIProvider
from app.ai.base.types import (
    AIHealth,
    AIProviderMetadata,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    MessageRole,
    TokenUsage,
)
from app.ai.exceptions import AICredentialError, AIGenerationError
from app.connectors.credentials.models import ConnectorCredentials

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_API_VERSION = "2023-06-01"


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude Messages API client."""

    def __init__(
        self,
        credentials: Optional[ConnectorCredentials] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        api_version: str = DEFAULT_API_VERSION,
        **dependencies: Any,
    ) -> None:
        super().__init__(
            credentials=credentials,
            api_key=api_key,
            base_url=base_url or DEFAULT_BASE_URL,
            timeout=timeout,
            **dependencies,
        )
        self.api_version = api_version

    def metadata(self) -> AIProviderMetadata:
        return AIProviderMetadata(
            name="claude",
            display_name="Anthropic Claude",
            version="1.0.0",
            description="Anthropic Claude Messages API",
            homepage="https://docs.anthropic.com",
            default_model=DEFAULT_MODEL,
            supported_models=[
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-latest",
                "claude-3-5-haiku-latest",
            ],
            capabilities=["generate", "health_check", "chat"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        api_key = self.require_api_key()
        system_text, messages = self._to_claude_messages(request)

        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
        }
        if system_text:
            payload["system"] = system_text
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop_sequences"] = request.stop

        data = await self._post_json("/messages", api_key, payload)
        try:
            blocks = data.get("content") or []
            content = "".join(
                block.get("text", "") for block in blocks if block.get("type") == "text"
            )
            finish_reason = data.get("stop_reason")
        except (TypeError, AttributeError) as exc:
            raise AIGenerationError(
                "Unexpected Claude response shape",
                details={"provider": "claude", "raw_keys": list(data.keys())},
            ) from exc

        usage_raw = data.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=usage_raw.get("input_tokens"),
            completion_tokens=usage_raw.get("output_tokens"),
            total_tokens=(
                (usage_raw.get("input_tokens") or 0)
                + (usage_raw.get("output_tokens") or 0)
                if usage_raw
                else None
            ),
        )
        return GenerateResponse(
            content=content,
            model=data.get("model", request.model),
            provider="claude",
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
        )

    async def health_check(self) -> AIHealth:
        started = time.perf_counter()
        try:
            api_key = self.require_api_key()
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
            assert self.base_url is not None
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                headers=self._headers(api_key),
                timeout=min(self.timeout, 15.0),
            ) as client:
                response = await client.post("/messages", json=payload)
                latency = (time.perf_counter() - started) * 1000
                if response.status_code == 401:
                    return AIHealth(
                        status=HealthStatus.UNHEALTHY,
                        provider="claude",
                        latency_ms=latency,
                        message="Invalid Claude API key",
                        details={"status_code": response.status_code},
                    )
                if response.status_code >= 400:
                    return AIHealth(
                        status=HealthStatus.DEGRADED,
                        provider="claude",
                        latency_ms=latency,
                        message=f"Claude health probe failed ({response.status_code})",
                        details={"status_code": response.status_code},
                    )
                return AIHealth(
                    status=HealthStatus.HEALTHY,
                    provider="claude",
                    latency_ms=latency,
                    message="ok",
                )
        except AICredentialError as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="claude",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=str(exc),
            )
        except Exception as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="claude",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=f"Claude health check error: {exc}",
            )

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

    def _to_claude_messages(
        self, request: GenerateRequest
    ) -> Tuple[str, List[Dict[str, str]]]:
        system_parts: List[str] = []
        messages: List[Dict[str, str]] = []
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_parts.append(msg.content)
                continue
            role = "assistant" if msg.role == MessageRole.ASSISTANT else "user"
            messages.append({"role": role, "content": msg.content})
        if not messages:
            messages.append({"role": "user", "content": ""})
        return "\n\n".join(system_parts), messages

    async def _post_json(
        self, path: str, api_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        assert self.base_url is not None
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                headers=self._headers(api_key),
                timeout=self.timeout,
            ) as client:
                response = await client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise AIGenerationError(
                f"Claude HTTP error: {exc}",
                details={"provider": "claude"},
            ) from exc

        if response.status_code == 401:
            raise AIGenerationError(
                "Claude authentication failed — check AI_CLAUDE_API_KEY",
                details={"provider": "claude", "status_code": 401},
            )
        if response.status_code >= 400:
            raise AIGenerationError(
                f"Claude API error ({response.status_code}): {response.text[:500]}",
                details={"provider": "claude", "status_code": response.status_code},
            )
        data = response.json()
        if not isinstance(data, dict):
            raise AIGenerationError(
                "Claude returned a non-object JSON body",
                details={"provider": "claude"},
            )
        return data

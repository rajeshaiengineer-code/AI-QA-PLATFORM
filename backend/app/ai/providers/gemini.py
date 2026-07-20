"""
Google Gemini generateContent provider (HTTP via httpx).
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

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-flash-latest"


class GeminiProvider(BaseAIProvider):
    """Google Gemini generateContent API client."""

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
            name="gemini",
            display_name="Google Gemini",
            version="1.0.0",
            description="Google Gemini generateContent API",
            homepage="https://ai.google.dev/docs",
            default_model=DEFAULT_MODEL,
            supported_models=[
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-2.0-flash",
                "gemini-2.5-flash",
            ],
            capabilities=["generate", "health_check", "chat"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        api_key = self.require_api_key()
        system_instruction, contents = self._to_gemini_payload(request)

        body: Dict[str, Any] = {"contents": contents}
        generation_config: Dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        if request.stop:
            generation_config["stopSequences"] = request.stop
        if generation_config:
            body["generationConfig"] = generation_config
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }

        path = f"/models/{request.model}:generateContent"
        data = await self._post_json(path, api_key, body)

        try:
            candidates = data.get("candidates") or []
            parts = candidates[0]["content"]["parts"]
            content = "".join(part.get("text", "") for part in parts)
            finish_reason = candidates[0].get("finishReason")
        except (KeyError, IndexError, TypeError) as exc:
            # Gemini sometimes returns promptFeedback without candidates
            feedback = data.get("promptFeedback")
            raise AIGenerationError(
                "Unexpected Gemini response shape",
                details={
                    "provider": "gemini",
                    "prompt_feedback": feedback,
                    "raw_keys": list(data.keys()),
                },
            ) from exc

        usage_meta = data.get("usageMetadata") or {}
        usage = TokenUsage(
            prompt_tokens=usage_meta.get("promptTokenCount"),
            completion_tokens=usage_meta.get("candidatesTokenCount"),
            total_tokens=usage_meta.get("totalTokenCount"),
        )
        return GenerateResponse(
            content=content,
            model=request.model,
            provider="gemini",
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
        )

    async def health_check(self) -> AIHealth:
        started = time.perf_counter()
        try:
            api_key = self.require_api_key()
            assert self.base_url is not None
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=min(self.timeout, 15.0),
            ) as client:
                response = await client.get(
                    f"/models/{DEFAULT_MODEL}",
                    params={"key": api_key},
                )
                latency = (time.perf_counter() - started) * 1000
                if response.status_code in (401, 403):
                    return AIHealth(
                        status=HealthStatus.UNHEALTHY,
                        provider="gemini",
                        latency_ms=latency,
                        message="Invalid Gemini API key",
                        details={"status_code": response.status_code},
                    )
                if response.status_code >= 400:
                    return AIHealth(
                        status=HealthStatus.DEGRADED,
                        provider="gemini",
                        latency_ms=latency,
                        message=f"Gemini health probe failed ({response.status_code})",
                        details={"status_code": response.status_code},
                    )
                return AIHealth(
                    status=HealthStatus.HEALTHY,
                    provider="gemini",
                    latency_ms=latency,
                    message="ok",
                )
        except AICredentialError as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="gemini",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=str(exc),
            )
        except Exception as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="gemini",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=f"Gemini health check error: {exc}",
            )

    def _to_gemini_payload(
        self, request: GenerateRequest
    ) -> Tuple[str, List[Dict[str, Any]]]:
        system_parts: List[str] = []
        contents: List[Dict[str, Any]] = []
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_parts.append(msg.content)
                continue
            role = "user" if msg.role == MessageRole.USER else "model"
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": msg.content}],
                }
            )
        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})
        return "\n\n".join(system_parts), contents

    async def _post_json(
        self, path: str, api_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        assert self.base_url is not None
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=self.timeout,
            ) as client:
                response = await client.post(
                    path,
                    params={"key": api_key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise AIGenerationError(
                f"Gemini HTTP error: {exc}",
                details={"provider": "gemini"},
            ) from exc

        if response.status_code in (401, 403):
            raise AIGenerationError(
                "Gemini authentication failed — check AI_GEMINI_API_KEY",
                details={"provider": "gemini", "status_code": response.status_code},
            )
        if response.status_code >= 400:
            raise AIGenerationError(
                f"Gemini API error ({response.status_code}): {response.text[:500]}",
                details={"provider": "gemini", "status_code": response.status_code},
            )
        data = response.json()
        if not isinstance(data, dict):
            raise AIGenerationError(
                "Gemini returned a non-object JSON body",
                details={"provider": "gemini"},
            )
        return data

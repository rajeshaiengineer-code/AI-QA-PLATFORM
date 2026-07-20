"""
Amazon Bedrock Converse API provider (HTTP via httpx + bearer API key).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

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

DEFAULT_REGION = "us-east-1"
DEFAULT_MODEL = "amazon.nova-lite-v1:0"


def bedrock_runtime_base_url(region: str) -> str:
    return f"https://bedrock-runtime.{region}.amazonaws.com"


class BedrockProvider(BaseAIProvider):
    """Amazon Bedrock Converse API client (Bearer token / API key auth)."""

    def __init__(
        self,
        credentials: Optional[ConnectorCredentials] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        region: Optional[str] = None,
        **dependencies: Any,
    ) -> None:
        self.region = (region or DEFAULT_REGION).strip()
        resolved_base = base_url or bedrock_runtime_base_url(self.region)
        super().__init__(
            credentials=credentials,
            api_key=api_key,
            base_url=resolved_base,
            timeout=timeout,
            **dependencies,
        )

    def metadata(self) -> AIProviderMetadata:
        return AIProviderMetadata(
            name="bedrock",
            display_name="Amazon Bedrock",
            version="1.0.0",
            description="Amazon Bedrock Converse API (API key / bearer token)",
            homepage="https://docs.aws.amazon.com/bedrock/",
            default_model=DEFAULT_MODEL,
            supported_models=[
                "amazon.nova-lite-v1:0",
                "amazon.nova-pro-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "us.anthropic.claude-3-5-haiku-20241022-v1:0",
            ],
            capabilities=["generate", "health_check", "chat"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        api_key = self.require_api_key()
        system_blocks, messages = self._to_bedrock_messages(request)

        payload: Dict[str, Any] = {"messages": messages}
        if system_blocks:
            payload["system"] = system_blocks

        inference: Dict[str, Any] = {}
        if request.max_tokens is not None:
            inference["maxTokens"] = request.max_tokens
        else:
            inference["maxTokens"] = 2048
        if request.temperature is not None:
            inference["temperature"] = request.temperature
        if request.top_p is not None:
            inference["topP"] = request.top_p
        if request.stop:
            inference["stopSequences"] = request.stop
        if inference:
            payload["inferenceConfig"] = inference

        data = await self._post_converse(api_key, request.model, payload)
        try:
            content_blocks = (
                ((data.get("output") or {}).get("message") or {}).get("content") or []
            )
            content = "".join(
                block.get("text", "")
                for block in content_blocks
                if isinstance(block, dict) and block.get("text")
            )
            finish_reason = data.get("stopReason")
        except (TypeError, AttributeError) as exc:
            raise AIGenerationError(
                "Unexpected Bedrock response shape",
                details={"provider": "bedrock", "raw_keys": list(data.keys())},
            ) from exc

        usage_raw = data.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=usage_raw.get("inputTokens"),
            completion_tokens=usage_raw.get("outputTokens"),
            total_tokens=usage_raw.get("totalTokens")
            or (
                (usage_raw.get("inputTokens") or 0)
                + (usage_raw.get("outputTokens") or 0)
                if usage_raw
                else None
            ),
        )
        return GenerateResponse(
            content=content,
            model=request.model,
            provider="bedrock",
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
        )

    async def health_check(self) -> AIHealth:
        started = time.perf_counter()
        try:
            api_key = self.require_api_key()
            payload = {
                "messages": [
                    {"role": "user", "content": [{"text": "ping"}]}
                ],
                "inferenceConfig": {"maxTokens": 8},
            }
            await self._post_converse(
                api_key,
                DEFAULT_MODEL,
                payload,
                timeout=min(self.timeout, 20.0),
            )
            latency = (time.perf_counter() - started) * 1000
            return AIHealth(
                status=HealthStatus.HEALTHY,
                provider="bedrock",
                latency_ms=latency,
                message="ok",
            )
        except AICredentialError as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="bedrock",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=str(exc),
            )
        except AIGenerationError as exc:
            status = HealthStatus.UNHEALTHY
            details = exc.details or {}
            code = details.get("status_code")
            if code and int(code) >= 400 and int(code) < 500 and int(code) != 401:
                status = HealthStatus.DEGRADED
            return AIHealth(
                status=status,
                provider="bedrock",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=str(exc),
                details=details,
            )
        except Exception as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="bedrock",
                latency_ms=(time.perf_counter() - started) * 1000,
                message=f"Bedrock health check error: {exc}",
            )

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _to_bedrock_messages(
        self, request: GenerateRequest
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        system_blocks: List[Dict[str, str]] = []
        messages: List[Dict[str, Any]] = []
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_blocks.append({"text": msg.content})
                continue
            role = "assistant" if msg.role == MessageRole.ASSISTANT else "user"
            messages.append(
                {"role": role, "content": [{"text": msg.content}]}
            )
        if not messages:
            messages.append({"role": "user", "content": [{"text": ""}]})
        return system_blocks, messages

    async def _post_converse(
        self,
        api_key: str,
        model_id: str,
        payload: Dict[str, Any],
        *,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        assert self.base_url is not None
        encoded_model = quote(model_id, safe="")
        path = f"/model/{encoded_model}/converse"
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                headers=self._headers(api_key),
                timeout=timeout or self.timeout,
            ) as client:
                response = await client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise AIGenerationError(
                f"Bedrock HTTP error: {exc}",
                details={"provider": "bedrock"},
            ) from exc

        if response.status_code in (401, 403):
            raise AIGenerationError(
                "Bedrock authentication failed — check AI_BEDROCK_API_KEY "
                "and model access in your AWS account",
                details={
                    "provider": "bedrock",
                    "status_code": response.status_code,
                },
            )
        if response.status_code >= 400:
            raise AIGenerationError(
                f"Bedrock API error ({response.status_code}): "
                f"{response.text[:500]}",
                details={
                    "provider": "bedrock",
                    "status_code": response.status_code,
                },
            )
        data = response.json()
        if not isinstance(data, dict):
            raise AIGenerationError(
                "Bedrock returned a non-object JSON body",
                details={"provider": "bedrock"},
            )
        return data

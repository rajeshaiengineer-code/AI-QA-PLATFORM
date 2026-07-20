"""
Unit tests for the AI Framework (registry, factory, prompts, models, providers).

HTTP calls are mocked — no real provider API requests.
"""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai import (
    AICredentialError,
    AIGenerationError,
    AIModelNotFoundError,
    AIProviderAlreadyRegisteredError,
    AIProviderDisabledError,
    AIProviderFactory,
    AIProviderNotFoundError,
    AIProviderRegistry,
    BaseAIProvider,
    ChatMessage,
    ClaudeProvider,
    GenerateRequest,
    GenerateResponse,
    GeminiProvider,
    HealthStatus,
    MessageRole,
    ModelBinding,
    ModelRegistry,
    OpenAIProvider,
    PromptManager,
    PromptNotFoundError,
    PromptRenderError,
)
from app.ai.base.types import AIHealth, AIProviderMetadata
from app.ai.config import AIConfig, AISettings
from app.ai.runtime import register_builtin_ai_providers
from app.connectors.base.types import CredentialType
from app.connectors.credentials import CredentialManager, InMemoryCredentialStore
from app.connectors.credentials.models import ConnectorCredentials


class MockAIProvider(BaseAIProvider):
    """Test-only provider — not a production implementation."""

    def metadata(self) -> AIProviderMetadata:
        return AIProviderMetadata(
            name="mock-ai",
            display_name="Mock AI",
            version="1.0.0",
            default_model="mock-1",
            capabilities=["generate", "health_check"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.require_api_key()
        return GenerateResponse(
            content="mock-response",
            model=request.model,
            provider="mock-ai",
            finish_reason="stop",
        )

    async def health_check(self) -> AIHealth:
        try:
            self.require_api_key()
            return AIHealth(status=HealthStatus.HEALTHY, provider="mock-ai", message="ok")
        except AICredentialError as exc:
            return AIHealth(
                status=HealthStatus.UNHEALTHY,
                provider="mock-ai",
                message=str(exc),
            )


def _make_request(model: str = "gpt-4o-mini") -> GenerateRequest:
    return GenerateRequest(
        model=model,
        messages=[ChatMessage(role=MessageRole.USER, content="hello")],
        max_tokens=32,
    )


def _mock_async_client(
    *,
    json_data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    text: str = "",
    get_json: Optional[Dict[str, Any]] = None,
    get_status: int = 200,
) -> MagicMock:
    """Build a mock httpx.AsyncClient usable as an async context manager."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text or str(json_data)
    response.json.return_value = json_data or {}

    get_response = MagicMock()
    get_response.status_code = get_status
    get_response.json.return_value = get_json if get_json is not None else {"data": []}

    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=get_response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# Registry / Factory
# ---------------------------------------------------------------------------


class TestAIProviderRegistry:
    def setup_method(self) -> None:
        self.registry = AIProviderRegistry()

    def test_register_and_get(self) -> None:
        self.registry.register(MockAIProvider)
        entry = self.registry.get("mock-ai")
        assert entry.name == "mock-ai"
        assert entry.provider_class is MockAIProvider
        assert "mock-ai" in self.registry.list_names()

    def test_duplicate_registration_raises(self) -> None:
        self.registry.register(MockAIProvider)
        with pytest.raises(AIProviderAlreadyRegisteredError):
            self.registry.register(MockAIProvider)

    def test_enable_disable(self) -> None:
        self.registry.register(MockAIProvider)
        self.registry.disable("mock-ai")
        with pytest.raises(AIProviderDisabledError):
            self.registry.get("mock-ai")
        self.registry.enable("mock-ai")
        assert self.registry.is_enabled("mock-ai") is True

    def test_not_found(self) -> None:
        with pytest.raises(AIProviderNotFoundError):
            self.registry.get("missing")


class TestAIProviderFactory:
    def setup_method(self) -> None:
        self.registry = AIProviderRegistry()
        self.registry.register(MockAIProvider)
        self.credentials = CredentialManager(store=InMemoryCredentialStore())
        self.factory = AIProviderFactory(
            registry=self.registry,
            credential_manager=self.credentials,
        )

    def test_create_loads_credentials(self) -> None:
        self.credentials.save(
            ConnectorCredentials(
                connector_name="mock-ai",
                credential_type=CredentialType.API_KEY,
                api_key="secret-key",
            )
        )
        provider = self.factory.create("mock-ai")
        assert provider.resolve_api_key() == "secret-key"

    def test_create_explicit_api_key(self) -> None:
        provider = self.factory.create("mock-ai", api_key="explicit", load_credentials=False)
        assert provider.resolve_api_key() == "explicit"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_clear_error(self) -> None:
        provider = self.factory.create("mock-ai", load_credentials=False)
        with pytest.raises(AICredentialError) as exc:
            await provider.generate(_make_request())
        assert "API key missing" in str(exc.value)
        assert "mock-ai" in str(exc.value)

    @pytest.mark.asyncio
    async def test_generate_with_key(self) -> None:
        provider = self.factory.create("mock-ai", api_key="k", load_credentials=False)
        result = await provider.generate(_make_request())
        assert result.content == "mock-response"
        assert result.provider == "mock-ai"


# ---------------------------------------------------------------------------
# PromptManager / ModelRegistry / AIConfig
# ---------------------------------------------------------------------------


class TestPromptManager:
    def setup_method(self) -> None:
        self.manager = PromptManager()

    def test_list_and_load_builtin_templates(self) -> None:
        names = self.manager.list_templates()
        assert "echo" in names
        assert "health_check" in names
        text = self.manager.load("echo")
        assert "$message" in text

    def test_render_substitutes_variables(self) -> None:
        rendered = self.manager.render("echo", {"message": "ping"})
        assert "ping" in rendered
        assert "$message" not in rendered

    def test_missing_template(self) -> None:
        with pytest.raises(PromptNotFoundError):
            self.manager.load("does-not-exist")

    def test_missing_variable(self) -> None:
        with pytest.raises(PromptRenderError):
            self.manager.render("echo", {})


class TestModelRegistry:
    def setup_method(self) -> None:
        self.registry = ModelRegistry()

    def test_register_and_resolve(self) -> None:
        self.registry.register(
            ModelBinding(
                logical_name="fast",
                provider="openai",
                model="gpt-4o-mini",
            )
        )
        binding = self.registry.resolve("fast")
        assert binding.provider == "openai"
        assert binding.model == "gpt-4o-mini"

    def test_not_found(self) -> None:
        with pytest.raises(AIModelNotFoundError):
            self.registry.get("missing")


class TestAIConfig:
    def test_api_key_and_base_url_helpers(self) -> None:
        cfg = AIConfig(
            AISettings(
                AI_OPENAI_API_KEY="sk-test",
                AI_GEMINI_API_KEY=None,
                AI_CLAUDE_API_KEY="claude-key",
            )
        )
        assert cfg.api_key_for("openai") == "sk-test"
        assert cfg.api_key_for("gemini") is None
        assert cfg.base_url_for("openai") == "https://api.openai.com/v1"
        assert cfg.default_provider == "openai"


# ---------------------------------------------------------------------------
# Provider HTTP clients (mocked)
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        client = _mock_async_client(
            json_data={
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "hi there"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 2,
                    "total_tokens": 7,
                },
            }
        )
        with patch("app.ai.providers.openai.httpx.AsyncClient", return_value=client):
            result = await provider.generate(_make_request())
        assert result.content == "hi there"
        assert result.provider == "openai"
        assert result.usage is not None
        assert result.usage.total_tokens == 7
        client.post.assert_awaited()

    @pytest.mark.asyncio
    async def test_missing_key(self) -> None:
        provider = OpenAIProvider()
        with pytest.raises(AICredentialError) as exc:
            await provider.generate(_make_request())
        assert "AI_OPENAI_API_KEY" in str(exc.value) or "openai" in str(exc.value)

    @pytest.mark.asyncio
    async def test_api_error(self) -> None:
        provider = OpenAIProvider(api_key="sk-bad")
        client = _mock_async_client(status_code=500, text="boom", json_data={"error": "x"})
        with patch("app.ai.providers.openai.httpx.AsyncClient", return_value=client):
            with pytest.raises(AIGenerationError):
                await provider.generate(_make_request())

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        client = _mock_async_client(get_status=200, get_json={"data": []})
        with patch("app.ai.providers.openai.httpx.AsyncClient", return_value=client):
            health = await provider.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert health.provider == "openai"


class TestGeminiProvider:
    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        provider = GeminiProvider(api_key="gem-test")
        client = _mock_async_client(
            json_data={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "gemini says hi"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 3,
                    "candidatesTokenCount": 4,
                    "totalTokenCount": 7,
                },
            }
        )
        with patch("app.ai.providers.gemini.httpx.AsyncClient", return_value=client):
            result = await provider.generate(
                GenerateRequest(
                    model="gemini-2.0-flash",
                    messages=[
                        ChatMessage(role=MessageRole.SYSTEM, content="be brief"),
                        ChatMessage(role=MessageRole.USER, content="hi"),
                    ],
                )
            )
        assert result.content == "gemini says hi"
        assert result.provider == "gemini"
        client.post.assert_awaited()

    @pytest.mark.asyncio
    async def test_missing_key(self) -> None:
        provider = GeminiProvider()
        with pytest.raises(AICredentialError):
            await provider.generate(
                GenerateRequest(
                    model="gemini-2.0-flash",
                    messages=[ChatMessage(role=MessageRole.USER, content="x")],
                )
            )


class TestClaudeProvider:
    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        provider = ClaudeProvider(api_key="claude-test")
        client = _mock_async_client(
            json_data={
                "model": "claude-sonnet-4-20250514",
                "content": [{"type": "text", "text": "claude says hi"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 4, "output_tokens": 3},
            }
        )
        with patch("app.ai.providers.claude.httpx.AsyncClient", return_value=client):
            result = await provider.generate(
                GenerateRequest(
                    model="claude-sonnet-4-20250514",
                    messages=[
                        ChatMessage(role=MessageRole.SYSTEM, content="sys"),
                        ChatMessage(role=MessageRole.USER, content="hi"),
                    ],
                )
            )
        assert result.content == "claude says hi"
        assert result.provider == "claude"
        assert result.usage is not None
        assert result.usage.total_tokens == 7

    @pytest.mark.asyncio
    async def test_missing_key(self) -> None:
        provider = ClaudeProvider()
        with pytest.raises(AICredentialError) as exc:
            await provider.generate(
                GenerateRequest(
                    model="claude-sonnet-4-20250514",
                    messages=[ChatMessage(role=MessageRole.USER, content="x")],
                )
            )
        assert "claude" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Runtime registration
# ---------------------------------------------------------------------------


class TestAIRuntime:
    def test_register_builtin_providers_idempotent(self) -> None:
        from app.ai import runtime as ai_runtime
        from app.connectors.runtime import credential_manager as shared_creds

        previous_factory_creds = ai_runtime.ai_factory.credential_manager
        ai_runtime.ai_provider_registry.clear()
        ai_runtime.model_registry.clear()
        store = InMemoryCredentialStore()
        manager = CredentialManager(store=store)

        try:
            register_builtin_ai_providers(
                credential_manager=manager,
                config=AIConfig(
                    AISettings(
                        AI_OPENAI_API_KEY="sk-from-env",
                        AI_DEFAULT_PROVIDER="openai",
                    )
                ),
            )
            register_builtin_ai_providers(credential_manager=manager)

            assert set(ai_runtime.ai_provider_registry.list_names()) == {
                "openai",
                "gemini",
                "claude",
            }
            assert "default" in ai_runtime.model_registry.list_names()
            loaded = manager.require("openai")
            assert loaded.get_secret_value("api_key") == "sk-from-env"
        finally:
            ai_runtime.ai_factory.credential_manager = (
                previous_factory_creds or shared_creds
            )
            # Re-seed builtins for any later tests that expect them
            register_builtin_ai_providers()

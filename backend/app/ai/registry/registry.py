"""
AI Provider Registry — dynamic registration and discovery of plugins.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from app.ai.base.provider import BaseAIProvider
from app.ai.base.types import AIProviderMetadata
from app.ai.exceptions import (
    AIProviderAlreadyRegisteredError,
    AIProviderDisabledError,
    AIProviderNotFoundError,
)


@dataclass
class AIProviderRegistration:
    """Bookkeeping entry for a registered AI provider class."""

    name: str
    provider_class: Type[BaseAIProvider]
    enabled: bool = True
    metadata: Optional[AIProviderMetadata] = field(default=None, repr=False)

    def resolve_metadata(self) -> AIProviderMetadata:
        if self.metadata is not None:
            return self.metadata
        return self.provider_class().metadata()


class AIProviderRegistry:
    """
    Process-wide registry of AI provider plugins.

    Providers register their class; the Factory instantiates instances.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, AIProviderRegistration] = {}

    def register(
        self,
        provider_class: Type[BaseAIProvider],
        *,
        name: Optional[str] = None,
        enabled: bool = True,
        overwrite: bool = False,
    ) -> AIProviderRegistration:
        """Register an AI provider class dynamically."""
        instance_meta = provider_class().metadata()
        key = (name or instance_meta.name).strip().lower()
        if not key:
            raise ValueError("AI provider name must not be blank")
        if key in self._entries and not overwrite:
            raise AIProviderAlreadyRegisteredError(key)

        registration = AIProviderRegistration(
            name=key,
            provider_class=provider_class,
            enabled=enabled,
            metadata=instance_meta,
        )
        self._entries[key] = registration
        return registration

    def unregister(self, name: str) -> bool:
        return self._entries.pop(name.strip().lower(), None) is not None

    def get(self, name: str, *, require_enabled: bool = True) -> AIProviderRegistration:
        key = name.strip().lower()
        entry = self._entries.get(key)
        if entry is None:
            raise AIProviderNotFoundError(key)
        if require_enabled and not entry.enabled:
            raise AIProviderDisabledError(key)
        return entry

    def get_class(
        self, name: str, *, require_enabled: bool = True
    ) -> Type[BaseAIProvider]:
        return self.get(name, require_enabled=require_enabled).provider_class

    def list_installed(
        self, *, enabled_only: bool = False
    ) -> List[AIProviderRegistration]:
        entries = list(self._entries.values())
        if enabled_only:
            return [e for e in entries if e.enabled]
        return entries

    def list_names(self, *, enabled_only: bool = False) -> List[str]:
        return [e.name for e in self.list_installed(enabled_only=enabled_only)]

    def enable(self, name: str) -> None:
        entry = self.get(name, require_enabled=False)
        entry.enabled = True

    def disable(self, name: str) -> None:
        entry = self.get(name, require_enabled=False)
        entry.enabled = False

    def is_registered(self, name: str) -> bool:
        return name.strip().lower() in self._entries

    def is_enabled(self, name: str) -> bool:
        entry = self._entries.get(name.strip().lower())
        return bool(entry and entry.enabled)

    def clear(self) -> None:
        """Remove all registrations (primarily for tests)."""
        self._entries.clear()


default_ai_registry = AIProviderRegistry()

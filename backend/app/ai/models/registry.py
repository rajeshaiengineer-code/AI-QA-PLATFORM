"""
Model Registry — map logical model names to provider + remote model id.
"""

from typing import Dict, List, Optional

from app.ai.base.types import ModelBinding
from app.ai.exceptions import AIModelNotFoundError


class ModelRegistry:
    """
    Application-facing model catalog.

    Callers ask for a logical name (e.g. ``fast``, ``balanced``); the registry
    resolves the concrete provider and model string for the factory.
    """

    def __init__(self) -> None:
        self._bindings: Dict[str, ModelBinding] = {}

    def register(self, binding: ModelBinding, *, overwrite: bool = False) -> ModelBinding:
        key = binding.logical_name.strip().lower()
        if not key:
            raise ValueError("logical_name must not be blank")
        if key in self._bindings and not overwrite:
            raise ValueError(f"Logical model '{key}' is already registered")
        normalized = binding.model_copy(
            update={
                "logical_name": key,
                "provider": binding.provider.strip().lower(),
            }
        )
        self._bindings[key] = normalized
        return normalized

    def register_many(
        self, bindings: List[ModelBinding], *, overwrite: bool = False
    ) -> None:
        for binding in bindings:
            self.register(binding, overwrite=overwrite)

    def get(self, logical_name: str, *, require_enabled: bool = True) -> ModelBinding:
        key = logical_name.strip().lower()
        binding = self._bindings.get(key)
        if binding is None:
            raise AIModelNotFoundError(key)
        if require_enabled and not binding.enabled:
            raise AIModelNotFoundError(key)
        return binding

    def resolve(self, logical_name: str) -> ModelBinding:
        """Alias for get() — resolve logical name to provider/model."""
        return self.get(logical_name)

    def list_bindings(self, *, enabled_only: bool = False) -> List[ModelBinding]:
        values = list(self._bindings.values())
        if enabled_only:
            return [b for b in values if b.enabled]
        return values

    def list_names(self, *, enabled_only: bool = False) -> List[str]:
        return [b.logical_name for b in self.list_bindings(enabled_only=enabled_only)]

    def unregister(self, logical_name: str) -> bool:
        return self._bindings.pop(logical_name.strip().lower(), None) is not None

    def clear(self) -> None:
        self._bindings.clear()

    def get_or_none(self, logical_name: str) -> Optional[ModelBinding]:
        return self._bindings.get(logical_name.strip().lower())

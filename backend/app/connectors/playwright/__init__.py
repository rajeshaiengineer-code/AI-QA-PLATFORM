"""
Playwright connector package.

Stub for future browser automation / execution connector.
Generation of Playwright TypeScript lives in ``app.services.playwright_generator``;
this package will later wrap local or remote Playwright execution (CLI / CDP).
"""

from typing import Any, Dict

__all__ = ["PlaywrightConnectorStub"]


class PlaywrightConnectorStub:
    """
    Placeholder connector surface for the Connector Framework.

    Not registered in ``register_builtin_connectors()`` until a real
    BaseConnector implementation exists. Kept for discoverability and
    future DI wiring.
    """

    name: str = "playwright"
    display_name: str = "Playwright"
    category: str = "automation"

    def metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "status": "stub",
            "capabilities": ["generate", "execute_stub"],
            "notes": (
                "Generation is handled by PlaywrightGeneratorService; "
                "MVP execution uses StubTestRunner (no real browsers). "
                "See ExecutionEngineService / docs/ExecutionEngine.md."
            ),
        }

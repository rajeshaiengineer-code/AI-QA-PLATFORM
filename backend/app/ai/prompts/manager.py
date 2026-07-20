"""
PromptManager — load and render text templates from the prompts directory.
"""

from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Union

from app.ai.exceptions import PromptNotFoundError, PromptRenderError

# Default templates live next to this package: app/ai/prompts/*.txt (and templates/)
_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent


class PromptManager:
    """
    File-backed prompt loader with ``$variable`` / ``${variable}`` substitution.

    Search order for a name ``foo``:
      1. ``{prompts_dir}/foo.txt``
      2. ``{prompts_dir}/foo.md``
      3. ``{prompts_dir}/templates/foo.txt``
      4. ``{prompts_dir}/templates/foo.md``
    """

    def __init__(self, prompts_dir: Optional[Union[str, Path]] = None) -> None:
        self.prompts_dir = Path(prompts_dir) if prompts_dir else _DEFAULT_PROMPTS_DIR
        self._cache: Dict[str, str] = {}

    def list_templates(self) -> List[str]:
        """Return logical template names (without extension)."""
        names = set()
        for pattern in ("*.txt", "*.md"):
            for path in self.prompts_dir.glob(pattern):
                if path.is_file() and path.name != "README.md":
                    names.add(path.stem)
            templates_subdir = self.prompts_dir / "templates"
            if templates_subdir.is_dir():
                for path in templates_subdir.glob(pattern):
                    if path.is_file():
                        names.add(path.stem)
        return sorted(names)

    def load(self, name: str, *, use_cache: bool = True) -> str:
        """Load a raw template by logical name."""
        key = name.strip()
        if use_cache and key in self._cache:
            return self._cache[key]

        path = self._resolve_path(key)
        if path is None:
            raise PromptNotFoundError(key)

        text = path.read_text(encoding="utf-8")
        if use_cache:
            self._cache[key] = text
        return text

    def render(self, name: str, variables: Optional[Dict[str, object]] = None) -> str:
        """
        Load and render a template.

        Uses ``string.Template`` safe substitution rules; missing keys raise
        ``PromptRenderError``.
        """
        template_text = self.load(name)
        variables = variables or {}
        try:
            # Convert values to str for Template
            mapping = {k: "" if v is None else str(v) for k, v in variables.items()}
            return Template(template_text).substitute(mapping)
        except KeyError as exc:
            raise PromptRenderError(
                f"Missing prompt variable {exc} for template '{name}'",
                details={"template": name, "missing": str(exc).strip("'")},
            ) from exc
        except ValueError as exc:
            raise PromptRenderError(
                f"Invalid prompt template '{name}': {exc}",
                details={"template": name},
            ) from exc

    def clear_cache(self) -> None:
        self._cache.clear()

    def _resolve_path(self, name: str) -> Optional[Path]:
        # Prevent path traversal
        clean = name.replace("\\", "/").lstrip("/")
        if ".." in clean.split("/"):
            return None

        candidates = [
            self.prompts_dir / f"{clean}.txt",
            self.prompts_dir / f"{clean}.md",
            self.prompts_dir / "templates" / f"{clean}.txt",
            self.prompts_dir / "templates" / f"{clean}.md",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import exceptions as pai_exc


class Utilities:
    """Small file I/O helpers for consistent, readable output across the project."""

    def __init__(self) -> None:
        raise RuntimeError("Utilities is a static class; do not instantiate it.")
    
    @staticmethod
    def reset_dir(dir: Path) -> None:
        """Create dir and delete existing files inside it."""
        dir.mkdir(parents=True, exist_ok=True)
        for path in dir.iterdir():
            if path.is_file():
                path.unlink()

    @staticmethod
    def ensure_parent_dir(path: Path) -> None:
        """Create the parent directory for a file path (no-op if it already exists)."""
        path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_json(path: Path, model: BaseModel, *, indent: int = 2) -> None:
        """Write a Pydantic model to disk as pretty-printed JSON."""
        Utilities.ensure_parent_dir(path)
        path.write_text(model.model_dump_json(indent=indent), encoding="utf-8")

    @staticmethod
    def write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        """Write plain text to disk (overwrites existing file)."""
        Utilities.ensure_parent_dir(path)
        path.write_text(text, encoding=encoding)

    @staticmethod
    def write_bytes(path: Path, data: bytes) -> None:
        """Write raw bytes to disk (overwrites existing file)."""
        Utilities.ensure_parent_dir(path)
        path.write_bytes(data)

    @staticmethod
    def unwrap_model_retry_message(exception: BaseException) -> str | None:
        """
        Extract the underlying `ModelRetry` message from a wrapped PydanticAI exception chain.
        """
        current_exception: BaseException | None = exception
        while current_exception is not None:
            if isinstance(current_exception, pai_exc.ModelRetry):
                return str(current_exception)
            current_exception = current_exception.__cause__
        return None

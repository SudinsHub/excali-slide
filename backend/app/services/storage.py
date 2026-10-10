from pathlib import Path
from typing import Protocol

from app.config import settings
from app.errors import BadRequestError, NotFoundError


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or settings.storage_path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        # Prevent path traversal across OS platforms
        normalized = key.replace("\\", "/").lstrip("/")
        target_path = (self.base_dir / normalized).resolve()
        try:
            target_path.relative_to(self.base_dir)
        except ValueError:
            raise BadRequestError(
                code="path_traversal",
                message="Path traversal is not permitted",
                details={"key": key},
            ) from None
        return target_path

    def put(self, key: str, data: bytes) -> None:
        target_path = self._resolve_path(key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    def get(self, key: str) -> bytes:
        target_path = self._resolve_path(key)
        if not target_path.is_file():
            raise NotFoundError(
                message=f"Storage item '{key}' not found",
                details={"key": key},
            )
        return target_path.read_bytes()

    def delete(self, key: str) -> None:
        target_path = self._resolve_path(key)
        if target_path.is_file():
            target_path.unlink()

    def exists(self, key: str) -> bool:
        target_path = self._resolve_path(key)
        return target_path.is_file()


# Default singleton instance
storage = LocalStorage()

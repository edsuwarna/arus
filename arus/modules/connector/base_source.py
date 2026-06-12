from abc import ABC, abstractmethod
from typing import Iterator, Any
from dataclasses import dataclass, field


@dataclass
class TableSchema:
    name: str
    schema_name: str = "public"
    columns: list[dict] = field(default_factory=list)
    row_count_estimate: int = 0


@dataclass
class SyncMode:
    mode: str = "incremental"  # "incremental" or "full_refresh"
    watermark_column: str | None = None
    deleted_at_column: str | None = None


class BaseSource(ABC):
    type: str = ""

    @abstractmethod
    def connect(self, config: dict) -> bool: ...

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def discover_tables(self) -> list[TableSchema]: ...

    @abstractmethod
    def get_table_columns(self, table: str) -> list[dict]: ...

    @abstractmethod
    def detect_sync_mode(self, table: str, columns: list[dict]) -> SyncMode: ...

    @abstractmethod
    def extract(self, table: str, watermark: Any = None, batch_size: int = 10000) -> Iterator[list[dict]]: ...

    def extract_soft_deletes(self, table: str, watermark: Any,
                              deleted_at_column: str, watermark_column: str,
                              batch_size: int = 10000) -> list[dict]:
        """Extract soft-deleted rows since last watermark.

        Returns rows where deleted_at IS NOT NULL and deleted_at > watermark,
        but were NOT already caught by normal incremental extract
        (watermark_column <= watermark).

        Override in connectors that support soft-delete detection.
        Default returns empty — no soft-delete tracking.
        """
        return []

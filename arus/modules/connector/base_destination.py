from abc import ABC, abstractmethod
from typing import Any


class BaseDestination(ABC):
    type: str = ""

    @abstractmethod
    def connect(self, config: dict) -> bool: ...

    @abstractmethod
    def ensure_schema(self, source_name: str, table: str, columns: list[dict], target_schema: str = None) -> None: ...

    @abstractmethod
    def load_raw(self, source_name: str, table: str, rows: list[dict], run_id: str) -> int: ...

    @abstractmethod
    def load_normalized(self, source_name: str, table: str, rows: list[dict], target_schema: str = None) -> int: ...

    @abstractmethod
    def update_watermark(self, pipeline_id: str, table: str, value: Any) -> None: ...

    def delete_rows(self, source_name: str, table: str, rows: list[dict],
                    pk_columns: list[str], target_schema: str = None) -> int:
        """Delete rows from target table by primary key.

        Used for soft-delete reconciliation. Default implementation
        raises NotImplementedError — override in connectors that
        support soft-delete sync.
        """
        raise NotImplementedError("delete_rows not implemented for this destination")

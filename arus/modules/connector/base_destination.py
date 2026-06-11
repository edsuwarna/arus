from abc import ABC, abstractmethod
from typing import Any


class BaseDestination(ABC):
    type: str = ""

    @abstractmethod
    def connect(self, config: dict) -> bool: ...

    @abstractmethod
    def ensure_schema(self, source_name: str, table: str, columns: list[dict]) -> None: ...

    @abstractmethod
    def load_raw(self, source_name: str, table: str, rows: list[dict], run_id: str) -> int: ...

    @abstractmethod
    def load_normalized(self, source_name: str, table: str, rows: list[dict]) -> int: ...

    @abstractmethod
    def update_watermark(self, pipeline_id: str, table: str, value: Any) -> None: ...

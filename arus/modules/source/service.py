from arus.shared.exceptions import NotFoundError, DiscoveryFailedError
from arus.shared.crypto import decrypt_password
from arus.modules.connector.registry import get_source
from arus.modules.source.repository import SourceRepository


class SourceService:
    def __init__(self, repo: SourceRepository):
        self.repo = repo

    def _build_connector(self, source):
        connector_class = get_source(source.type)
        connector = connector_class()
        config = {
            "host": source.host,
            "port": source.port,
            "username": source.username,
            "password": decrypt_password(source.password_enc),
            "database": source.database,
            "ssl": source.ssl,
        }
        connector.connect(config)
        return connector

    def test_connection(self, source_id: str) -> dict:
        source = self.repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found")

        try:
            connector = self._build_connector(source)
            ok = connector.test_connection()
            source.status = "connected" if ok else "error"
        except Exception as e:
            source.status = "error"
            return {"connected": False, "error": str(e)}
        finally:
            self.repo.db.commit()

        return {"connected": ok}

    def discover_tables(self, source_id: str) -> list[dict]:
        source = self.repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found")

        try:
            connector = self._build_connector(source)
            tables = connector.discover_tables()
            result = []
            for t in tables:
                columns = t.columns or connector.get_table_columns(t.name)
                sync = connector.detect_sync_mode(t.name, columns)
                result.append({
                    "name": t.name,
                    "schema": t.schema_name,
                    "row_count_estimate": t.row_count_estimate,
                    "columns": columns,
                    "detected_sync": sync.mode,
                    "watermark_column": sync.watermark_column,
                    "enabled": True,
                })
            return result
        except Exception as e:
            raise DiscoveryFailedError(f"Discovery failed: {str(e)}")

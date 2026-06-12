"""MongoDB Source Connector — discovers collections, infers schema, streams docs."""
from typing import Iterator, Any
from datetime import datetime

import pymongo
from pymongo import MongoClient
from pymongo.operations import _IndexList
from bson.objectid import ObjectId

from arus.modules.connector.base_source import BaseSource, TableSchema, SyncMode


class MongoDBSource(BaseSource):
    type = "mongodb"

    def __init__(self):
        self.client = None
        self.config = {}
        self.db = None
        self.db_name = ""

    def connect(self, config: dict) -> bool:
        self.config = config
        self.db_name = config["database"]

        host = config.get("host", "localhost")
        port = config.get("port", 27017)
        username = config.get("username", "")
        password = config.get("password", "")
        ssl = config.get("ssl", False)

        # Build MongoDB URI
        if username and password:
            uri = (
                f"mongodb://{username}:{password}@{host}:{port}/"
                f"{self.db_name}?authSource={self.db_name}"
            )
        else:
            uri = f"mongodb://{host}:{port}/{self.db_name}"

        if ssl:
            uri += "&tls=true" if "?" in uri else "?tls=true"

        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Force check — will raise on failure
        self.client.admin.command("ping")
        self.db = self.client[self.db_name]
        return True

    def test_connection(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def discover_tables(self) -> list[TableSchema]:
        tables = []
        for collection_name in self.db.list_collection_names():
            try:
                row_estimate = self.db[collection_name].estimated_document_count()
            except Exception:
                row_estimate = 0
            columns = self.get_table_columns(collection_name)
            tables.append(
                TableSchema(
                    name=collection_name,
                    schema_name=self.db_name,
                    row_count_estimate=row_estimate,
                    columns=columns,
                )
            )
        return tables

    def get_table_columns(self, table: str) -> list[dict]:
        """Infer schema by sampling one document from the collection."""
        doc = self.db[table].find_one()
        if not doc:
            return []

        columns = []
        for key, value in doc.items():
            if key == "_id":
                columns.append({
                    "name": key,
                    "type": "varchar(48)",
                    "nullable": False,
                    "pk": True,
                })
            else:
                col_type = self._infer_type(value)
                columns.append({
                    "name": key,
                    "type": col_type,
                    "nullable": True,
                    "pk": False,
                })
        return columns

    def _infer_type(self, value) -> str:
        """Map a BSON/Python value to a logical type name."""
        if value is None:
            return "null"
        if isinstance(value, datetime):
            return "timestamp"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "bigint"
        if isinstance(value, float):
            return "double"
        if isinstance(value, dict):
            return "json"
        if isinstance(value, (list, tuple)):
            return "json"
        if isinstance(value, ObjectId):
            return "varchar(48)"
        if isinstance(value, bytes):
            return "binary"
        if isinstance(value, pymongo.collection.Collection):
            return "text"
        return "text"

    def detect_sync_mode(self, table: str, columns: list[dict]) -> SyncMode:
        ts_cols = {"updated_at", "modified_at", "last_modified", "updated"}
        for col in columns:
            if col["name"].lower() in ts_cols:
                return SyncMode(mode="incremental", watermark_column=col["name"])
        for col in columns:
            if col["name"].lower() == "created_at":
                return SyncMode(mode="incremental", watermark_column=col["name"])
        return SyncMode(mode="full_refresh", watermark_column=None)

    def extract(self, table: str, watermark: Any = None,
                batch_size: int = 10000) -> Iterator[list[dict]]:
        collection = self.db[table]

        # Detect watermark column from an empty or sample document
        wm_col = None
        sample = collection.find_one(projection={"_id": 0}, sort=[("$natural", pymongo.ASCENDING)])
        if sample:
            ts_candidates = {"updated_at", "modified_at",
                             "last_modified", "updated", "created_at"}
            wm_col = next((c for c in ts_candidates if c in sample), None)

        if watermark and wm_col:
            try:
                # Attempt to parse ISO datetime string
                wm_dt = datetime.fromisoformat(
                    watermark.replace("Z", "+00:00")
                )
                cursor = collection.find(
                    {wm_col: {"$gt": wm_dt}},
                    sort=[(wm_col, pymongo.ASCENDING)],
                    batch_size=batch_size,
                )
            except (ValueError, TypeError):
                cursor = collection.find(
                    {wm_col: {"$gt": watermark}},
                    sort=[(wm_col, pymongo.ASCENDING)],
                    batch_size=batch_size,
                )
        else:
            cursor = collection.find(batch_size=batch_size)

        batch = []
        for doc in cursor:
            # Serialise BSON types to JSON-safe values
            doc["_id"] = str(doc["_id"])
            for key, val in doc.items():
                if isinstance(val, datetime):
                    doc[key] = val.isoformat()
                elif isinstance(val, ObjectId):
                    doc[key] = str(val)
            batch.append(doc)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

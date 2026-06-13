"""Fixtures for pipeline executor unit tests.

This conftest pre-registers mock modules for database connectors (pymysql,
pymongo, clickhouse_driver) so that importing arus.modules.pipeline.executor
succeeds in the test environment without requiring real drivers.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Pre-register mock modules for missing database drivers
# ---------------------------------------------------------------------------
# These are needed because executor.py imports connector.registry, which
# eagerly imports all source/destination connector modules (mysql, mongo,
# clickhouse, etc.).  We stub them out so tests don't need real drivers.


def _mock_module(fullname: str, attrs: dict | None = None) -> types.ModuleType:
    """Create and register a fake module in sys.modules."""
    mod = types.ModuleType(fullname)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[fullname] = mod
    return mod


# pymysql + submodules
_mock_module("pymysql", {
    "connect": MagicMock(),
    "OperationalError": type("OperationalError", (Exception,), {}),
})
_mock_module("pymysql.cursors", {
    "DictCursor": type("DictCursor", (), {}),
})

# pymongo + submodules
_mock_module("pymongo", {
    "MongoClient": MagicMock(),
})
_mock_module("pymongo.operations", {
    "_IndexList": MagicMock(),
})

# clickhouse-driver
_mock_module("clickhouse_driver", {
    "Client": MagicMock(),
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_source():
    """A MagicMock simulating a source connector."""
    src = MagicMock()
    src.connect.return_value = True
    src.test_connection.return_value = True
    src.extract.return_value = iter([[{"id": 1, "name": "test"}]])
    src.get_table_columns.return_value = [
        {"name": "id", "type": "int", "nullable": False, "pk": True},
        {"name": "name", "type": "varchar", "nullable": True},
    ]
    return src


@pytest.fixture
def mock_destination():
    """A MagicMock simulating a destination connector."""
    dest = MagicMock()
    dest.connect.return_value = True
    dest.ensure_schema.return_value = None
    dest.load_raw.return_value = 1
    dest.load_normalized.return_value = 1
    return dest


@pytest.fixture
def source_config():
    """Sample source configuration for a MySQL source."""
    return {
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "user": "test_user",
        "password_enc": "encrypted_pass",
        "database": "test_db",
        "name": "test_source",
        "safe_name": "test_source",
    }


@pytest.fixture
def dest_config():
    """Sample destination configuration for a PostgreSQL dest."""
    return {
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "user": "test_user",
        "password": "test_pass",
        "database": "test_db",
        "name": "test_dest",
    }

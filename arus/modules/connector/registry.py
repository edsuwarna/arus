from arus.modules.connector.base_source import BaseSource
from arus.modules.connector.base_destination import BaseDestination
from arus.modules.connector.sources.mysql import MySQLSource
from arus.modules.connector.sources.postgresql import PostgreSQLSource
from arus.modules.connector.sources.mongo import MongoDBSource
from arus.modules.connector.destinations.postgresql import PostgreSQLDestination
from arus.modules.connector.destinations.clickhouse import ClickHouseDestination

_source_registry: dict[str, type[BaseSource]] = {}
_dest_registry: dict[str, type[BaseDestination]] = {}


def register_source(type_name: str, cls: type[BaseSource]):
    _source_registry[type_name] = cls


def register_destination(type_name: str, cls: type[BaseDestination]):
    _dest_registry[type_name] = cls


def get_source(type_name: str) -> type[BaseSource]:
    if type_name not in _source_registry:
        raise ValueError(f"Unknown source type: {type_name}. Available: {list(_source_registry.keys())}")
    return _source_registry[type_name]


def get_destination(type_name: str) -> type[BaseDestination]:
    if type_name not in _dest_registry:
        raise ValueError(f"Unknown destination type: {type_name}. Available: {list(_dest_registry.keys())}")
    return _dest_registry[type_name]


def list_sources() -> list[str]:
    return list(_source_registry.keys())


def list_destinations() -> list[str]:
    return list(_dest_registry.keys())


# Auto-register built-in connectors
register_source("mysql", MySQLSource)
register_source("mariadb", MySQLSource)  # MySQL-compatible
register_source("postgresql", PostgreSQLSource)
register_source("mongodb", MongoDBSource)
register_destination("postgresql", PostgreSQLDestination)
register_destination("clickhouse", ClickHouseDestination)

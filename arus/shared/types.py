TYPE_MAP = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "smallint": "SMALLINT",
    "bigint": "BIGINT",
    "serial": "BIGINT",
    "bigserial": "BIGINT",
    "decimal": "DECIMAL",
    "numeric": "DECIMAL",
    "float": "DOUBLE PRECISION",
    "double": "DOUBLE PRECISION",
    "varchar": "VARCHAR",
    "char": "VARCHAR",
    "text": "TEXT",
    "longtext": "TEXT",
    "boolean": "BOOLEAN",
    "tinyint": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMPTZ",
    "timestamp": "TIMESTAMPTZ",
    "json": "JSONB",
    "jsonb": "JSONB",
    "blob": "BYTEA",
    "binary": "BYTEA",
    "uuid": "UUID",
    "enum": "VARCHAR(255)",
}


def map_type(source_type: str) -> str:
    """Map source DB column type to PostgreSQL type."""
    base = source_type.lower().split("(")[0].split()[0]
    return TYPE_MAP.get(base, "TEXT")

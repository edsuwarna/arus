"""Tests for soft delete (deleted_at) filtering in source connector extract()."""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# PostgreSQL connector tests
# =============================================================================


def _make_pg_source():
    """Create a PostgreSQLSource with a mocked connection."""
    from arus.modules.connector.sources.postgresql import PostgreSQLSource

    source = PostgreSQLSource()
    source.conn = MagicMock()
    source.db_name = "testdb"
    return source


def _mock_pg_cursor(source):
    """Mock the PostgreSQL cursor context manager for extract() execute calls."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    # The extract() method calls cursor(cursor_factory=...) so accept any kwargs
    source.conn.cursor.return_value = mock_cursor
    return mock_cursor


def test_postgresql_extract_filters_deleted_at():
    """When deleted_at column exists, incremental extract should add 'deleted_at IS NULL'."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    # Deleted_at column is detected
    source._has_deleted_at_column = MagicMock(return_value=True)

    # Table has a watermark column (updated_at)
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "updated_at", "type": "timestamp", "nullable": True},
            {"name": "deleted_at", "type": "timestamp", "nullable": True},
        ]
    )

    # Extract with watermark (incremental mode)
    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert '"deleted_at" IS NULL' in sql, f"Expected deleted_at IS NULL in SQL:\n{sql}"
    assert "updated_at" in sql


def test_postgresql_extract_filters_deleted_at_full_refresh():
    """When deleted_at column exists, full refresh should add 'WHERE deleted_at IS NULL'."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)

    # Extract without watermark (full refresh)
    batches = list(source.extract("my_table"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert '"deleted_at" IS NULL' in sql, f"Expected deleted_at IS NULL in SQL:\n{sql}"
    # Full refresh with deleted_at should have WHERE but no ORDER BY
    assert "ORDER BY" not in sql


def test_postgresql_extract_skips_filter_when_no_deleted_at():
    """When no deleted_at column, SQL should NOT contain 'deleted_at'."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    # No deleted_at column detected
    source._has_deleted_at_column = MagicMock(return_value=False)

    # Table has watermark column
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "updated_at", "type": "timestamp", "nullable": True},
        ]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at" not in sql, f"Unexpected deleted_at in SQL:\n{sql}"


def test_postgresql_extract_skips_filter_full_refresh_no_deleted_at():
    """When no deleted_at column, full refresh should not add any WHERE clause."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=False)

    batches = list(source.extract("my_table"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at" not in sql
    assert "WHERE" not in sql


def test_postgresql_extract_filters_deleted_at_incremental_no_watermark_column():
    """With deleted_at + no watermark column, incremental extract should still filter."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)

    # Table has NO timestamp/watermark column
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "name", "type": "text", "nullable": True},
            {"name": "deleted_at", "type": "timestamp", "nullable": True},
        ]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert '"deleted_at" IS NULL' in sql, f"Expected deleted_at IS NULL in SQL:\n{sql}"


def test_postgresql_extract_with_schema_prefix():
    """Table with schema prefix (schema.table) should work correctly."""
    source = _make_pg_source()
    mock_cursor = _mock_pg_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "updated_at", "type": "timestamp", "nullable": True},
            {"name": "deleted_at", "type": "timestamp", "nullable": True},
        ]
    )

    batches = list(source.extract("custom_schema.my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert '"custom_schema"."my_table"' in sql
    assert '"deleted_at" IS NULL' in sql


# =============================================================================
# MySQL connector tests
# =============================================================================


def _make_mysql_source():
    """Create a MySQLSource with a mocked connection."""
    from arus.modules.connector.sources.mysql import MySQLSource

    source = MySQLSource()
    source.conn = MagicMock()
    source.db_name = "testdb"
    return source


def _mock_mysql_cursor(source):
    """Mock the MySQL cursor context manager for extract() execute calls."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    source.conn.cursor.return_value = mock_cursor
    return mock_cursor


def test_mysql_extract_filters_deleted_at():
    """When deleted_at column exists, MySQL extract should add 'deleted_at IS NULL'."""
    source = _make_mysql_source()
    mock_cursor = _mock_mysql_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "int", "nullable": False},
            {"name": "updated_at", "type": "datetime", "nullable": True},
            {"name": "deleted_at", "type": "datetime", "nullable": True},
        ]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at IS NULL" in sql, f"Expected deleted_at IS NULL in SQL:\n{sql}"


def test_mysql_extract_filters_deleted_at_full_refresh():
    """When deleted_at column exists, MySQL full refresh should add 'WHERE deleted_at IS NULL'."""
    source = _make_mysql_source()
    mock_cursor = _mock_mysql_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)

    batches = list(source.extract("my_table"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at IS NULL" in sql, f"Expected deleted_at IS NULL in SQL:\n{sql}"
    assert "ORDER BY" not in sql


def test_mysql_extract_skips_filter_when_no_deleted_at():
    """When no deleted_at column, MySQL SQL should NOT contain 'deleted_at'."""
    source = _make_mysql_source()
    mock_cursor = _mock_mysql_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=False)
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "int", "nullable": False},
            {"name": "updated_at", "type": "datetime", "nullable": True},
        ]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at" not in sql, f"Unexpected deleted_at in SQL:\n{sql}"


def test_mysql_extract_skips_filter_full_refresh_no_deleted_at():
    """When no deleted_at column, MySQL full refresh should not add WHERE."""
    source = _make_mysql_source()
    mock_cursor = _mock_mysql_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=False)

    batches = list(source.extract("my_table"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at" not in sql
    assert "WHERE" not in sql


def test_mysql_extract_filters_deleted_at_incremental_no_watermark_column():
    """MySQL: With deleted_at + no watermark column, should still filter."""
    source = _make_mysql_source()
    mock_cursor = _mock_mysql_cursor(source)

    source._has_deleted_at_column = MagicMock(return_value=True)
    source.get_table_columns = MagicMock(
        return_value=[
            {"name": "id", "type": "int", "nullable": False},
            {"name": "name", "type": "varchar(100)", "nullable": True},
            {"name": "deleted_at", "type": "datetime", "nullable": True},
        ]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))

    assert mock_cursor.execute.called
    sql = mock_cursor.execute.call_args[0][0]
    assert "deleted_at IS NULL" in sql

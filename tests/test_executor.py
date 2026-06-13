"""Unit tests for PipelineExecutor using mocked connectors."""

from unittest.mock import MagicMock, patch

import pytest

from arus.modules.pipeline.executor import PipelineExecutor


class TestPipelineExecutor:
    """Test suite for PipelineExecutor run() method."""

    @patch("arus.modules.pipeline.executor.get_source")
    @patch("arus.modules.pipeline.executor.get_destination")
    @patch("arus.modules.pipeline.executor.decrypt_password")
    def test_run_with_single_table(
        self,
        mock_decrypt,
        mock_get_dest,
        mock_get_src,
        mock_source,
        mock_destination,
        source_config,
        dest_config,
    ):
        """Executor processes one table and returns success with rows."""
        # Arrange
        mock_decrypt.return_value = "decrypted_pass"
        mock_get_src.return_value = MagicMock(return_value=mock_source)
        mock_get_dest.return_value = MagicMock(return_value=mock_destination)

        executor = PipelineExecutor(source_config, dest_config)
        tables = [
            {
                "source_table": "users",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "pk": True},
                    {"name": "name", "type": "varchar", "nullable": True},
                ],
                "load_mode": "direct",
                "sync_mode": "incremental",
                "watermark_column": "updated_at",
            }
        ]

        # Act
        result = executor.run("pipeline-1", tables)

        # Assert
        assert result["status"] == "success"
        assert result["rows_synced"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["table"] == "users"
        assert result["results"][0]["status"] == "success"
        assert result["results"][0]["rows"] == 1
        assert result["run_id"] is not None

        # Verify connectors were created
        mock_get_src.assert_called_once_with("mysql")
        mock_get_dest.assert_called_once_with("postgresql")

        # Password was decrypted
        mock_decrypt.assert_called_once_with("encrypted_pass")

        # Destination: ensure_schema + load_normalized called
        mock_source.connect.assert_called_once()
        mock_source.extract.assert_called_once()
        mock_destination.connect.assert_called_once()
        mock_destination.ensure_schema.assert_called_once()
        mock_destination.load_normalized.assert_called_once()

    @patch("arus.modules.pipeline.executor.get_source")
    @patch("arus.modules.pipeline.executor.get_destination")
    @patch("arus.modules.pipeline.executor.decrypt_password")
    def test_run_with_empty_extract(
        self,
        mock_decrypt,
        mock_get_dest,
        mock_get_src,
        mock_source,
        mock_destination,
        source_config,
        dest_config,
    ):
        """Source returns no rows; executor reports 0 rows; load_raw not called."""
        # Arrange
        mock_decrypt.return_value = "decrypted_pass"
        mock_get_src.return_value = MagicMock(return_value=mock_source)
        mock_get_dest.return_value = MagicMock(return_value=mock_destination)
        # Source returns no rows (empty batch)
        mock_source.extract.return_value = iter([[]])

        executor = PipelineExecutor(source_config, dest_config)
        tables = [
            {
                "source_table": "users",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "pk": True},
                ],
                "load_mode": "direct",
            }
        ]

        # Act
        result = executor.run("pipeline-1", tables)

        # Assert
        assert result["status"] == "success"
        assert result["rows_synced"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["rows"] == 0
        assert result["results"][0]["status"] == "success"

        # Extract was called, but load_normalized was NOT called (0 rows -> early continue)
        mock_source.extract.assert_called_once()
        mock_destination.load_raw.assert_not_called()
        mock_destination.load_normalized.assert_not_called()

    @patch("arus.modules.pipeline.executor.get_source")
    @patch("arus.modules.pipeline.executor.get_destination")
    @patch("arus.modules.pipeline.executor.decrypt_password")
    def test_run_handles_extraction_failure(
        self,
        mock_decrypt,
        mock_get_dest,
        mock_get_src,
        mock_source,
        mock_destination,
        source_config,
        dest_config,
    ):
        """Source raises during extract; executor returns failed per-table status."""
        # Arrange
        mock_decrypt.return_value = "decrypted_pass"
        mock_get_src.return_value = MagicMock(return_value=mock_source)
        mock_get_dest.return_value = MagicMock(return_value=mock_destination)
        # Source raises on extract
        mock_source.extract.side_effect = Exception("Connection lost")

        executor = PipelineExecutor(source_config, dest_config)
        tables = [
            {
                "source_table": "users",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "pk": True},
                ],
            }
        ]

        # Act
        result = executor.run("pipeline-1", tables)

        # Assert
        # The extraction failure is caught per-table (ExtractionError in the table loop)
        # so the overall pipeline status remains success, but the individual
        # table result reports failure.
        assert result["status"] == "success"
        assert result["rows_synced"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["table"] == "users"
        assert result["results"][0]["status"] == "failed"
        assert result["results"][0]["rows"] == 0
        assert "failed" in result["results"][0]["error"].lower()

        # Extract was attempted (multiple calls due to tenacity retry), but no load ops
        assert mock_source.extract.call_count >= 1
        mock_destination.load_raw.assert_not_called()
        mock_destination.load_normalized.assert_not_called()

    @patch("arus.modules.pipeline.executor.get_source")
    @patch("arus.modules.pipeline.executor.get_destination")
    @patch("arus.modules.pipeline.executor.decrypt_password")
    def test_run_multiple_tables(
        self,
        mock_decrypt,
        mock_get_dest,
        mock_get_src,
        mock_source,
        mock_destination,
        source_config,
        dest_config,
    ):
        """Two tables processed; rows_synced is the sum of both."""
        # Arrange
        mock_decrypt.return_value = "decrypted_pass"
        mock_get_src.return_value = MagicMock(return_value=mock_source)
        mock_get_dest.return_value = MagicMock(return_value=mock_destination)
        # Return different row counts per call using side_effect
        mock_source.extract.side_effect = [
            iter([[{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]]),
            iter([[{"id": 3, "name": "charlie"}]]),
        ]

        executor = PipelineExecutor(source_config, dest_config)
        tables = [
            {
                "source_table": "users",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "pk": True},
                    {"name": "name", "type": "varchar", "nullable": True},
                ],
                "load_mode": "direct",
            },
            {
                "source_table": "orders",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "pk": True},
                ],
                "load_mode": "direct",
            },
        ]

        # Act
        result = executor.run("pipeline-1", tables)

        # Assert
        assert result["status"] == "success"
        assert result["rows_synced"] == 3  # 2 + 1
        assert len(result["results"]) == 2

        # First table: 2 rows
        assert result["results"][0]["table"] == "users"
        assert result["results"][0]["rows"] == 2
        assert result["results"][0]["status"] == "success"

        # Second table: 1 row
        assert result["results"][1]["table"] == "orders"
        assert result["results"][1]["rows"] == 1
        assert result["results"][1]["status"] == "success"

        # Extract was called twice (once per table)
        assert mock_source.extract.call_count == 2
        # ensure_schema called for both tables
        assert mock_destination.ensure_schema.call_count == 2
        # load_normalized called for both tables
        assert mock_destination.load_normalized.call_count == 2

"""Tests for dashboard API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _patch_engine_imports():
    """Prevent the database engine from being created at import time.

    The session.py module creates a real create_engine() at module level,
    which triggers psycopg2 import and would try to connect when any
    query is executed.  We patch create_engine before any app imports
    so that no real DB connection is ever attempted.
    """
    from sqlalchemy import create_engine as real_create_engine
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = RuntimeError(
        "No real database available in tests"
    )

    with patch("sqlalchemy.create_engine", return_value=mock_engine):
        yield


@pytest.fixture(scope="module")
def test_app():
    """Build a minimal FastAPI app with only the dashboard router and
    overridable dependencies for auth and DB.

    This avoids the real app's startup event (which tries to run
    Alembic migrations and seed data against a real PostgreSQL DB).
    """
    from arus.modules.dashboard.router import router as dashboard_router
    from arus.shared.db.session import get_db
    from arus.modules.auth.router import get_current_user

    app = FastAPI(title="Arus Test API")
    app.include_router(dashboard_router)
    return app, get_db, get_current_user


@pytest.fixture
def mock_db():
    """Create a mock DB session."""
    return MagicMock()


@pytest.fixture
def admin_user():
    """Return a mock admin user dict."""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@arus.io",
        "name": "Arus Admin",
        "role": "admin",
        "is_active": True,
    }


@pytest.fixture
def client(test_app, mock_db, admin_user):
    """Create a TestClient with overridden auth and db dependencies."""
    app, get_db, get_current_user = test_app

    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _mock_query_factory(return_values=None):
    """
    Build a callable that can serve as db.query(...) side_effect.

    Each call returns a fresh MagicMock whose chained methods
    (.filter, .order_by, .limit, .distinct, .count, .scalar, .all)
    use the next value from *return_values* when a terminal method
    (.count, .scalar, .all) is called.

    *return_values* is an iterable consumed one-at-a-time across
    multiple db.query() calls.  If None, every terminal method returns
    a safe default (0 for count, 0 for scalar, [] for all).
    """
    return_values = iter(return_values or [])

    def _query(model):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.distinct.return_value = q
        q.offset.return_value = q

        def _count():
            try:
                return next(return_values)
            except StopIteration:
                return 0

        def _scalar():
            try:
                return next(return_values)
            except StopIteration:
                return 0

        def _all():
            try:
                val = next(return_values)
                return val if isinstance(val, list) else [val]
            except StopIteration:
                return []

        q.count.side_effect = _count
        q.scalar.side_effect = _scalar
        q.all.side_effect = _all
        return q

    return _query


class TestDashboardSummary:
    """Tests for GET /api/dashboard/summary."""

    def test_summary_returns_expected_fields(self, client, mock_db):
        """Verify summary endpoint returns all expected fields with correct types."""
        # The summary endpoint makes many db.query calls:
        #   - multiple count() calls and scalar() calls
        # Provide enough return values for all queries
        values = [
            3,  # active_sources count
            10,  # total_sources count
            5,  # total_destinations count
            8,  # total_pipelines count
            4,  # active_pipelines count
            2,  # total_runs_24h count
            1,  # failed_runs_24h count
            5000,  # rows_24h scalar (sum of rows_synced in 24h)
            2,  # sources_this_week count
            4,  # running_pipelines count
            1,  # failed_pipelines count (distinct count)
            15,  # total_tables_synced count (enabled)
            100000,  # total_rows_synced scalar (sum rows_synced where status=success)
            6,  # runs_7d_total count
            5,  # runs_7d_success count
            450,  # avg_latency_ms scalar
        ]

        mock_db.query.side_effect = _mock_query_factory(values)

        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

        summary = data["data"]

        # Check the four fields the task explicitly asks about
        expected_fields = [
            "active_sources",
            "total_rows_synced",
            "rows_synced_24h",
            "avg_latency_ms",
        ]
        for field in expected_fields:
            assert field in summary, f"Missing expected field: {field}"

        # Verify correct types
        assert isinstance(summary["active_sources"], int)
        assert isinstance(summary["total_rows_synced"], int)
        assert isinstance(summary["rows_synced_24h"], int)
        assert isinstance(summary["avg_latency_ms"], int)

        # Verify values match what we provided
        assert summary["active_sources"] == 3
        assert summary["total_rows_synced"] == 100000
        assert summary["rows_synced_24h"] == 5000
        assert summary["avg_latency_ms"] == 450


class TestDashboardRecentRuns:
    """Tests for GET /api/dashboard/recent-runs."""

    def test_recent_runs_has_rows_synced(self, client, mock_db):
        """Verify each run in recent-runs has rows_synced as int."""
        # Create mock Run objects
        mock_run1 = MagicMock()
        mock_run1.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        mock_run1.pipeline_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        mock_run1.status = "success"
        mock_run1.rows_synced = 1500
        mock_run1.duration_ms = 2340
        mock_run1.started_at = "2026-06-13T10:00:00"

        mock_run2 = MagicMock()
        mock_run2.id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        mock_run2.pipeline_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        mock_run2.status = "failed"
        mock_run2.rows_synced = 0
        mock_run2.duration_ms = None
        mock_run2.started_at = "2026-06-12T22:00:00"

        mock_run3 = MagicMock()
        mock_run3.id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        mock_run3.pipeline_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_run3.status = "success"
        mock_run3.rows_synced = None  # Edge case: None should become 0
        mock_run3.duration_ms = 500
        mock_run3.started_at = "2026-06-12T15:00:00"

        mock_runs = [mock_run1, mock_run2, mock_run3]

        # Setup the query chain for recent-runs
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_runs
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        response = client.get("/api/dashboard/recent-runs?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

        runs = data["data"]
        assert len(runs) == 3

        for run in runs:
            assert "rows_synced" in run, f"Run {run.get('id')} missing rows_synced"
            assert isinstance(run["rows_synced"], int), (
                f"rows_synced should be int, got {type(run['rows_synced']).__name__}"
            )

        # Verify specific values
        assert runs[0]["rows_synced"] == 1500
        assert runs[1]["rows_synced"] == 0
        # None should be converted to 0 by the endpoint: r.rows_synced or 0
        assert runs[2]["rows_synced"] == 0

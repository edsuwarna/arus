from sqlalchemy.orm import Session
from sqlalchemy import desc

from arus.modules.run_log.models import Run, RunTableStat, RunLog


class RunLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, pipeline_id: str, trigger_type: str = "scheduled") -> Run:
        run = Run(pipeline_id=pipeline_id, trigger_type=trigger_type)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_run(self, run_id: str, data: dict) -> None:
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            for k, v in data.items():
                setattr(run, k, v)
            self.db.commit()

    def get_runs(self, pipeline_id: str, limit: int = 20, offset: int = 0) -> list[Run]:
        return (
            self.db.query(Run)
            .filter(Run.pipeline_id == pipeline_id)
            .order_by(desc(Run.started_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_runs_by_asset(
        self, pipeline_id: str, asset_name: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Get runs for a pipeline, joined with RunTableStat filtered by asset_name.
        Returns per-asset metrics instead of pipeline-level totals."""
        rows = (
            self.db.query(Run, RunTableStat)
            .join(RunTableStat, RunTableStat.run_id == Run.id)
            .filter(Run.pipeline_id == pipeline_id)
            .filter(RunTableStat.table_name == asset_name)
            .order_by(desc(Run.started_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(run.Run.id),
                "pipeline_id": str(run.Run.pipeline_id),
                "status": run.Run.status,
                "started_at": run.Run.started_at,
                "finished_at": run.Run.finished_at,
                "trigger_type": run.Run.trigger_type,
                "rows_synced": (
                    (run.RunTableStat.rows_loaded_analytics or 0)
                    + (run.RunTableStat.rows_loaded_raw or 0)
                ),
                "duration_ms": run.RunTableStat.duration_ms or run.Run.duration_ms,
                "error_message": run.RunTableStat.error_message or run.Run.error_message,
            }
            for run in rows
        ]

    def get_recent_runs(self, limit: int = 10) -> list[Run]:
        return self.db.query(Run).order_by(desc(Run.started_at)).limit(limit).all()

    def add_table_stat(self, run_id: str, data: dict) -> None:
        stat = RunTableStat(run_id=run_id, **data)
        self.db.add(stat)
        self.db.commit()

    def add_log(self, run_id: str, level: str, message: str) -> None:
        log = RunLog(run_id=run_id, level=level, message=message)
        self.db.add(log)
        self.db.commit()

    def get_logs(self, run_id: str, limit: int = 100, offset: int = 0) -> list[RunLog]:
        return (
            self.db.query(RunLog)
            .filter(RunLog.run_id == run_id)
            .order_by(RunLog.id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def cancel_run(self, run_id: str) -> bool:
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return False
        if run.status not in ("running", "pending", "queued"):
            raise ValueError(f"Cannot cancel run with status '{run.status}'")
        run.status = "cancelled"
        self.db.commit()
        return True

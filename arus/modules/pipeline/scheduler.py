"""
APScheduler integration — handles cron scheduling for pipelines.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from arus.shared.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()
_jobs: dict[str, str] = {}  # pipeline_id → job_id


def start_scheduler():
    """Start the APScheduler background scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)


def _run_pipeline_job(pipeline_id: str):
    """Job function called by APScheduler — loads pipeline and executes it."""
    logger.info(f"Scheduled run triggered for pipeline {pipeline_id}")

    db = SessionLocal()
    try:
        from arus.modules.pipeline.service import PipelineService
        from arus.modules.pipeline.repository import PipelineRepository

        repo = PipelineRepository(db)
        svc = PipelineService(repo, db)

        pipeline = repo.get_by_id(pipeline_id)
        if not pipeline:
            logger.error(f"Scheduled pipeline {pipeline_id} not found in DB")
            return

        if pipeline.status != "active":
            logger.info(f"Pipeline {pipeline_id} status is {pipeline.status}, skipping scheduled run")
            return

        result = svc.trigger_pipeline(pipeline_id)
        status = result.get("status", "unknown")
        rows = result.get("rows_synced", 0)
        logger.info(f"Scheduled pipeline {pipeline_id} completed: status={status}, rows={rows}")
    except Exception as e:
        logger.exception(f"Scheduled pipeline {pipeline_id} failed: {e}")
    finally:
        db.close()


def schedule_pipeline(pipeline_id: str, cron_expr: str):
    """
    Schedule a pipeline to run on a cron expression.
    """
    # Remove existing job if any
    unschedule_pipeline(pipeline_id)

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        job = scheduler.add_job(
            _run_pipeline_job,
            trigger,
            args=[pipeline_id],
            id=f"pipeline_{pipeline_id}",
            name=pipeline_id,
        )
        _jobs[pipeline_id] = job.id
        logger.info(f"Scheduled pipeline {pipeline_id} with cron: {cron_expr}")
        return True
    except Exception as e:
        logger.error(f"Failed to schedule pipeline {pipeline_id}: {e}")
        return False


def unschedule_pipeline(pipeline_id: str):
    """Remove a pipeline from the scheduler."""
    if pipeline_id in _jobs:
        try:
            scheduler.remove_job(_jobs[pipeline_id])
        except Exception:
            pass
        del _jobs[pipeline_id]
        logger.info(f"Unscheduled pipeline {pipeline_id}")


def list_scheduled() -> list[str]:
    """List all scheduled pipeline IDs."""
    return list(_jobs.keys())


def load_scheduled_pipelines():
    """Load all active pipelines with schedules from DB into APScheduler."""
    db = SessionLocal()
    try:
        from arus.modules.pipeline.models import Pipeline

        pipelines = db.query(Pipeline).filter(
            Pipeline.schedule.isnot(None),
            Pipeline.schedule != "",
            Pipeline.status == "active",
        ).all()

        count = 0
        for p in pipelines:
            pid = str(p.id)
            ok = schedule_pipeline(pid, p.schedule)
            if ok:
                count += 1
                logger.info(f"Loaded schedule for pipeline {pid}: {p.schedule}")

        logger.info(f"Loaded {count}/{len(pipelines)} scheduled pipelines from DB")
    except Exception as e:
        logger.exception(f"Failed to load scheduled pipelines: {e}")
    finally:
        db.close()

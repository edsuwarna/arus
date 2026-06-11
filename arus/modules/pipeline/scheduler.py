"""
APScheduler integration — handles cron scheduling for pipelines.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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


def schedule_pipeline(pipeline_id: str, cron_expr: str, run_func):
    """
    Schedule a pipeline to run on a cron expression.
    run_func is a callable that executes the pipeline.
    """
    # Remove existing job if any
    unschedule_pipeline(pipeline_id)

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        job = scheduler.add_job(run_func, trigger, id=f"pipeline_{pipeline_id}", name=pipeline_id)
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


def list_scheduled() -> list[str]:
    """List all scheduled pipeline IDs."""
    return list(_jobs.keys())

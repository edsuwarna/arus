"""
Pipeline Dependency Resolver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Ensures pipelines run in order when they have dependencies (depends_on).

The executor checks dependencies before running:
if a dependency hasn't succeeded since the pipeline's last run, skip/wait.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from arus.modules.run_log.models import Run
from arus.modules.pipeline.models import Pipeline

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves and validates pipeline dependencies before execution."""

    def __init__(self, db_session):
        self.db = db_session

    def get_dependency(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get the pipeline that this pipeline depends on."""
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline or not pipeline.depends_on:
            return None
        dep = self.db.query(Pipeline).filter(Pipeline.id == pipeline.depends_on).first()
        return dep

    def check_dependency_satisfied(self, pipeline_id: str) -> dict:
        """
        Check if all dependencies for a pipeline are satisfied.

        Returns:
            {
                "satisfied": bool,
                "depends_on": str | None,
                "last_dep_run": dict | None,
                "reason": str | None,
            }
        """
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline or not pipeline.depends_on:
            return {
                "satisfied": True,
                "depends_on": None,
                "last_dep_run": None,
                "reason": None,
            }

        dep_pipeline_id = str(pipeline.depends_on)
        dep_pipeline = self.db.query(Pipeline).filter(Pipeline.id == dep_pipeline_id).first()
        dep_name = dep_pipeline.name if dep_pipeline else dep_pipeline_id

        # Find the last successful run of the dependency
        last_dep_run = (
            self.db.query(Run)
            .filter(
                Run.pipeline_id == dep_pipeline_id,
                Run.status == "success",
            )
            .order_by(Run.finished_at.desc())
            .first()
        )

        # Find the last run of the current pipeline (any status)
        last_this_run = (
            self.db.query(Run)
            .filter(Run.pipeline_id == pipeline_id)
            .order_by(Run.started_at.desc())
            .first()
        )

        if not last_dep_run:
            return {
                "satisfied": False,
                "depends_on": dep_pipeline_id,
                "last_dep_run": None,
                "reason": (
                    f"Dependency pipeline '{dep_name}' ({dep_pipeline_id}) "
                    f"has never succeeded"
                ),
            }

        # If this pipeline has never run, dependency is satisfied
        # (the dep has succeeded at least once)
        if not last_this_run:
            return {
                "satisfied": True,
                "depends_on": dep_pipeline_id,
                "last_dep_run": {
                    "id": str(last_dep_run.id),
                    "status": last_dep_run.status,
                    "finished_at": (
                        last_dep_run.finished_at.isoformat()
                        if last_dep_run.finished_at
                        else None
                    ),
                },
                "reason": None,
            }

        # Dependency must have succeeded since our last run
        if (
            last_dep_run.finished_at
            and last_this_run.started_at
            and last_dep_run.finished_at > last_this_run.started_at
        ):
            return {
                "satisfied": True,
                "depends_on": dep_pipeline_id,
                "last_dep_run": {
                    "id": str(last_dep_run.id),
                    "status": last_dep_run.status,
                    "finished_at": (
                        last_dep_run.finished_at.isoformat()
                        if last_dep_run.finished_at
                        else None
                    ),
                },
                "reason": None,
            }

        # Dependency hasn't succeeded since our last run
        return {
            "satisfied": False,
            "depends_on": dep_pipeline_id,
            "last_dep_run": {
                "id": str(last_dep_run.id),
                "status": last_dep_run.status,
                "finished_at": (
                    last_dep_run.finished_at.isoformat()
                    if last_dep_run.finished_at
                    else None
                ),
            },
            "reason": (
                f"Dependency pipeline '{dep_name}' last succeeded at "
                f"{last_dep_run.finished_at.isoformat() if last_dep_run.finished_at else 'N/A'}, "
                f"but this pipeline last ran at "
                f"{last_this_run.started_at.isoformat() if last_this_run.started_at else 'N/A'}.\n"
                f"Dependency must succeed after this pipeline's last run."
            ),
        }

    def get_topological_order(self, pipeline_ids: list[str]) -> list[str]:
        """
        Sort pipeline IDs in topological order based on depends_on relationships.
        Uses Kahn's algorithm for topological sort.
        """
        # Build adjacency and in-degree
        pipelines = self.db.query(Pipeline).filter(Pipeline.id.in_(pipeline_ids)).all()
        pipe_map = {str(p.id): p for p in pipelines}

        # Build graph
        adj = {pid: [] for pid in pipeline_ids}
        in_degree = {pid: 0 for pid in pipeline_ids}

        for pid in pipeline_ids:
            p = pipe_map.get(pid)
            if p and p.depends_on:
                dep_id = str(p.depends_on)
                if dep_id in pipe_map:
                    adj[dep_id].append(pid)
                    in_degree[pid] = in_degree.get(pid, 0) + 1

        # Kahn's algorithm
        queue = [pid for pid in pipeline_ids if in_degree.get(pid, 0) == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If there are cycles, remaining nodes go to the end
        remaining = [pid for pid in pipeline_ids if pid not in result]
        result.extend(remaining)

        return result

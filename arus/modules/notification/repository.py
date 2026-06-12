import json
import logging

from sqlalchemy.orm import Session

from arus.modules.notification.models import NotificationTarget, PipelineNotification

logger = logging.getLogger(__name__)


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    # -- NotificationTarget --
    def list_targets(self) -> list[dict]:
        q = self.db.query(NotificationTarget).order_by(NotificationTarget.created_at.desc()).all()
        return [self._target_to_dict(t) for t in q]

    def get_target(self, target_id: str) -> dict | None:
        t = self.db.query(NotificationTarget).filter(NotificationTarget.id == target_id).first()
        return self._target_to_dict(t) if t else None

    def create_target(self, data: dict) -> dict:
        t = NotificationTarget(
            name=data["name"],
            type=data["type"],
            config=json.dumps(data["config"]),
            is_active=data.get("is_active", True),
        )
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return self._target_to_dict(t)

    def update_target(self, target_id: str, data: dict) -> dict | None:
        t = self.db.query(NotificationTarget).filter(NotificationTarget.id == target_id).first()
        if not t:
            return None
        if "name" in data:
            t.name = data["name"]
        if "type" in data:
            t.type = data["type"]
        if "config" in data:
            t.config = json.dumps(data["config"])
        if "is_active" in data:
            t.is_active = data["is_active"]
        self.db.commit()
        self.db.refresh(t)
        return self._target_to_dict(t)

    def delete_target(self, target_id: str) -> bool:
        t = self.db.query(NotificationTarget).filter(NotificationTarget.id == target_id).first()
        if not t:
            return False
        self.db.delete(t)
        self.db.commit()
        return True

    def _target_to_dict(self, t) -> dict:
        return {
            "id": str(t.id),
            "name": t.name,
            "type": t.type,
            "config": json.loads(t.config) if isinstance(t.config, str) else t.config,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    # -- PipelineNotification --
    def list_by_pipeline(self, pipeline_id: str) -> list[dict]:
        from sqlalchemy import text
        sql = text("""
            SELECT pn.id, pn.pipeline_id, pn.target_id, pn.event_types, pn.created_at,
                   nt.name as target_name, nt.type as target_type
            FROM arus_config.pipeline_notifications pn
            JOIN arus_config.notification_targets nt ON nt.id = pn.target_id
            WHERE pn.pipeline_id = :pid
            ORDER BY pn.created_at DESC
        """)
        rows = self.db.execute(sql, {"pid": pipeline_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_pipeline_notification(self, data: dict) -> dict:
        pn = PipelineNotification(
            pipeline_id=data["pipeline_id"],
            target_id=data["target_id"],
            event_types=data.get("event_types", ["failure"]),
        )
        self.db.add(pn)
        self.db.commit()
        self.db.refresh(pn)
        return self._pn_to_dict(pn)

    def update_pipeline_notification(self, pn_id: str, data: dict) -> dict | None:
        pn = self.db.query(PipelineNotification).filter(PipelineNotification.id == pn_id).first()
        if not pn:
            return None
        if "event_types" in data:
            pn.event_types = data["event_types"]
        self.db.commit()
        self.db.refresh(pn)
        return self._pn_to_dict(pn)

    def delete_pipeline_notification(self, pn_id: str) -> bool:
        pn = self.db.query(PipelineNotification).filter(PipelineNotification.id == pn_id).first()
        if not pn:
            return False
        self.db.delete(pn)
        self.db.commit()
        return True

    def _pn_to_dict(self, pn) -> dict:
        return {
            "id": str(pn.id),
            "pipeline_id": str(pn.pipeline_id),
            "target_id": str(pn.target_id),
            "event_types": list(pn.event_types) if pn.event_types else [],
            "created_at": pn.created_at.isoformat() if pn.created_at else None,
        }

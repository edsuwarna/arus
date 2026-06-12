from sqlalchemy.orm import Session

from arus.modules.pipeline.models import TransformScript


class TransformScriptRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_pipeline(self, pipeline_id: str, limit: int = 0, offset: int = 0) -> list[TransformScript]:
        q = self.db.query(TransformScript).filter(
            TransformScript.pipeline_id == pipeline_id,
        ).order_by(TransformScript.created_at.desc())
        if limit > 0:
            q = q.offset(offset).limit(limit)
        return q.all()

    def count_by_pipeline(self, pipeline_id: str) -> int:
        return self.db.query(TransformScript).filter(
            TransformScript.pipeline_id == pipeline_id,
        ).count()

    def get_by_id(self, script_id: str) -> TransformScript | None:
        return self.db.query(TransformScript).filter(
            TransformScript.id == script_id,
        ).first()

    def get_by_name(self, pipeline_id: str, name: str) -> TransformScript | None:
        return self.db.query(TransformScript).filter(
            TransformScript.pipeline_id == pipeline_id,
            TransformScript.name == name,
        ).first()

    def create(self, pipeline_id: str, data: dict) -> TransformScript:
        script = TransformScript(pipeline_id=pipeline_id, **data)
        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)
        return script

    def update(self, script: TransformScript, data: dict) -> TransformScript:
        for k, v in data.items():
            setattr(script, k, v)
        self.db.commit()
        self.db.refresh(script)
        return script

    def delete(self, script: TransformScript) -> None:
        self.db.delete(script)
        self.db.commit()

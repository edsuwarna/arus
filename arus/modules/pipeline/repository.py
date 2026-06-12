from sqlalchemy.orm import Session

from arus.modules.pipeline.models import Pipeline, PipelineTable, Watermark


class PipelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, limit: int = 0, offset: int = 0) -> list[Pipeline]:
        q = self.db.query(Pipeline).order_by(Pipeline.created_at.desc())
        if limit > 0:
            q = q.offset(offset).limit(limit)
        return q.all()

    def count_all(self) -> int:
        return self.db.query(Pipeline).count()

    def get_by_id(self, pipeline_id: str) -> Pipeline | None:
        return self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

    def get_by_source(self, source_id: str) -> Pipeline | None:
        return self.db.query(Pipeline).filter(Pipeline.source_id == source_id).first()

    def create(self, data: dict) -> Pipeline:
        p = Pipeline(**data)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def update(self, pipeline: Pipeline, data: dict) -> Pipeline:
        for k, v in data.items():
            setattr(pipeline, k, v)
        self.db.commit()
        self.db.refresh(pipeline)
        return pipeline

    def delete(self, pipeline: Pipeline) -> None:
        self.db.delete(pipeline)
        self.db.commit()

    def get_tables(self, pipeline_id: str) -> list[PipelineTable]:
        return self.db.query(PipelineTable).filter(
            PipelineTable.pipeline_id == pipeline_id,
            PipelineTable.enabled == True,
        ).all()

    def set_tables(self, pipeline_id: str, tables: list[dict]) -> None:
        """Replace all tables for a pipeline."""
        self.db.query(PipelineTable).filter(PipelineTable.pipeline_id == pipeline_id).delete()
        for t in tables:
            pt = PipelineTable(pipeline_id=pipeline_id, **t)
            self.db.add(pt)
        self.db.commit()

    def get_watermark(self, pipeline_id: str, table: str) -> Watermark | None:
        return self.db.query(Watermark).filter(
            Watermark.pipeline_id == pipeline_id,
            Watermark.source_table == table,
        ).first()

    def set_watermark(self, pipeline_id: str, table: str, col: str | None, value: str | None) -> None:
        wm = self.get_watermark(pipeline_id, table)
        if wm:
            wm.watermark_value = value
            wm.watermark_col = col
            wm.last_synced_at = None
        else:
            wm = Watermark(
                pipeline_id=pipeline_id,
                source_table=table,
                watermark_col=col,
                watermark_value=value,
            )
            self.db.add(wm)
        self.db.commit()

from sqlalchemy.orm import Session

from arus.modules.source.models import Source


class SourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Source]:
        return self.db.query(Source).order_by(Source.created_at.desc()).offset(offset).limit(limit).all()

    def count_all(self) -> int:
        return self.db.query(Source).count()

    def get_by_id(self, source_id: str) -> Source | None:
        return self.db.query(Source).filter(Source.id == source_id).first()

    def create(self, data: dict) -> Source:
        source = Source(**data)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def update(self, source: Source, data: dict) -> Source:
        for k, v in data.items():
            setattr(source, k, v)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete(self, source: Source) -> None:
        self.db.delete(source)
        self.db.commit()

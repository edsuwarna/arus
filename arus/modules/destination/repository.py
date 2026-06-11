from sqlalchemy.orm import Session
from arus.modules.destination.models import Destination


class DestinationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Destination]:
        return self.db.query(Destination).order_by(Destination.created_at.desc()).all()

    def get_by_id(self, dest_id: str) -> Destination | None:
        return self.db.query(Destination).filter(Destination.id == dest_id).first()

    def get_default(self) -> Destination | None:
        return self.db.query(Destination).filter(Destination.is_default == True).first()

    def create(self, data: dict) -> Destination:
        dest = Destination(**data)
        self.db.add(dest)
        self.db.commit()
        self.db.refresh(dest)
        return dest

    def update(self, dest: Destination, data: dict) -> Destination:
        for k, v in data.items():
            setattr(dest, k, v)
        self.db.commit()
        self.db.refresh(dest)
        return dest

    def delete(self, dest: Destination) -> None:
        self.db.delete(dest)
        self.db.commit()

from sqlalchemy.orm import Session

from arus.modules.auth.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def create(self, email: str, name: str, password_hash: str, role: str = "viewer") -> User:
        user = User(email=email, name=name, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_all(self, limit: int = 0, offset: int = 0) -> list[User]:
        q = self.db.query(User).order_by(User.created_at.desc())
        if limit > 0:
            q = q.offset(offset).limit(limit)
        return q.all()

    def count_all(self) -> int:
        return self.db.query(User).count()

    def update(self, user_id: str, **kwargs) -> User | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        for key, val in kwargs.items():
            if val is not None and hasattr(user, key):
                setattr(user, key, val)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True

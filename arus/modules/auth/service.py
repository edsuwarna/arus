from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

from arus.shared.config import settings
from arus.shared.exceptions import AuthError
from arus.modules.auth.repository import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_token(self, user_id: str, role: str) -> tuple[str, datetime]:
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {"sub": user_id, "role": role, "exp": expires}
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        return token, expires

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return payload
        except JWTError:
            raise AuthError("Invalid or expired token")

    def login(self, email: str, password: str) -> dict:
        user = self.repo.get_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is disabled")

        token, expires = self.create_token(str(user.id), user.role)
        user.last_login = datetime.now(timezone.utc)
        return {
            "token": token,
            "user": {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
            "expires_at": expires,
        }

    def get_current_user(self, token: str) -> dict:
        payload = self.verify_token(token)
        user = self.repo.get_by_id(payload["sub"])
        if not user:
            raise AuthError("User not found")
        return {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role}

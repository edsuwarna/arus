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

    def _create_access_token(self, user_id: str, role: str) -> tuple[str, datetime]:
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        payload = {"sub": user_id, "role": role, "exp": expires, "type": "access"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        return token, expires

    def _create_refresh_token(self, user_id: str, role: str) -> tuple[str, datetime]:
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        payload = {"sub": user_id, "role": role, "exp": expires, "type": "refresh"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        return token, expires

    def create_token_pair(self, user_id: str, role: str) -> dict:
        access_token, access_exp = self._create_access_token(user_id, role)
        refresh_token, refresh_exp = self._create_refresh_token(user_id, role)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,  # 15 min in seconds
            "refresh_expires_in": 604800,  # 7 days in seconds
        }

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return payload
        except JWTError:
            raise AuthError("Invalid or expired token")

    def refresh_access_token(self, refresh_token_str: str) -> dict:
        payload = self.verify_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type — expected refresh token")

        user = self.repo.get_by_id(payload["sub"])
        if not user:
            raise AuthError("User not found")
        if not user.is_active:
            raise AuthError("Account is disabled")

        return self.create_token_pair(str(user.id), user.role)

    def login(self, email: str, password: str) -> dict:
        user = self.repo.get_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is disabled")

        tokens = self.create_token_pair(str(user.id), user.role)
        user.last_login = datetime.now(timezone.utc)
        return {
            **tokens,
            "user": {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        }

    def get_current_user(self, token: str) -> dict:
        payload = self.verify_token(token)
        if payload.get("type") != "access":
            raise AuthError("Invalid token type — expected access token")
        user = self.repo.get_by_id(payload["sub"])
        if not user:
            raise AuthError("User not found")
        return {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role}

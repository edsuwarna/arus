from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import AuthError
from arus.modules.auth.schemas import LoginRequest, UserCreate
from arus.modules.auth.service import AuthService
from arus.modules.auth.repository import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)) -> dict:
    if not token:
        raise AuthError("Authorization header required")
    if token.startswith("Bearer "):
        token = token[7:]
    service = AuthService(UserRepository(db))
    return service.get_current_user(token)


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise AuthError("Admin access required")
    return current_user


@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(UserRepository(db))
    result = service.login(req.email, req.password)
    return {"status": "ok", "data": result}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"status": "ok", "data": current_user}


@router.post("/users")
async def create_user(req: UserCreate, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    service = AuthService(UserRepository(db))
    hashed = service.hash_password(req.password)
    repo = UserRepository(db)
    user = repo.create(email=req.email, name=req.name, password_hash=hashed, role=req.role)
    return {"status": "ok", "data": {"id": str(user.id)}}

import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import AuthError
from arus.modules.auth.schemas import LoginRequest, UserCreate, UserUpdate
from arus.modules.auth.service import AuthService
from arus.modules.auth.repository import UserRepository

# ── Simple in-memory rate limiter ────────────────────────────────────────
_LOGIN_LIMIT = 10        # max attempts
_LOGIN_WINDOW = 60       # seconds
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _rate_limit_login(request: Request):
    """Dependency: rate-limit login by client IP."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _LOGIN_WINDOW

    # Prune old entries
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > window_start]

    if len(_login_attempts[ip]) >= _LOGIN_LIMIT:
        from arus.shared.exceptions import AuthError
        raise AuthError("Too many login attempts. Try again later.")

    _login_attempts[ip].append(now)


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


def require_editor_or_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "editor"):
        raise AuthError("Editor or admin access required")
    return current_user


@router.post("/login")
async def login(req: LoginRequest, _: None = Depends(_rate_limit_login), db: Session = Depends(get_db)):
    service = AuthService(UserRepository(db))
    result = service.login(req.email, req.password)
    return {"status": "ok", "data": result}


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout — invalidates session on client side. JWT tokens are stateless."""
    return {"status": "ok", "data": {"message": "Logged out"}}


@router.post("/refresh")
async def refresh(refresh_token: str = Header(None, alias="X-Refresh-Token"), db: Session = Depends(get_db)):
    if not refresh_token:
        raise AuthError("X-Refresh-Token header required")
    service = AuthService(UserRepository(db))
    result = service.refresh_access_token(refresh_token)
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


@router.get("/users")
async def list_users(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    repo = UserRepository(db)
    users = repo.list_all(limit=limit, offset=offset)
    total = repo.count_all()
    return {
        "status": "ok",
        "data": {
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "name": u.name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    repo = UserRepository(db)
    up = {k: v for k, v in req.model_dump(exclude_none=True).items() if v is not None}
    if 'password' in up:
        service = AuthService(repo)
        up['password_hash'] = service.hash_password(up.pop('password'))
    if not up:
        raise AuthError("No fields to update")
    user = repo.update(user_id, **up)
    if not user:
        raise AuthError("User not found")
    return {
        "status": "ok",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    repo = UserRepository(db)
    # Prevent deleting yourself
    current_id = admin["id"]
    if user_id == current_id:
        raise AuthError("Cannot delete your own account")
    deleted = repo.delete(user_id)
    if not deleted:
        raise AuthError("User not found")
    return {"status": "ok", "message": "User deleted"}

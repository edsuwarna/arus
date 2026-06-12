from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.crypto import encrypt_password
from arus.shared.exceptions import NotFoundError
from arus.modules.destination.schemas import DestinationCreate, DestinationUpdate
from arus.modules.destination.repository import DestinationRepository
from arus.modules.auth.router import get_current_user, require_editor_or_admin

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


@router.get("")
async def list_destinations(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    repo = DestinationRepository(db)
    destinations = repo.list_all(limit=limit, offset=offset)
    total = repo.count_all()
    return {
        "status": "ok",
        "data": {
            "destinations": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "type": d.type,
                    "host": d.host,
                    "port": d.port,
                    "database": d.database,
                    "status": d.status,
                    "raw_schema": d.raw_schema,
                    "target_schema": d.target_schema,
                    "is_default": d.is_default,
                    "total_tables": 0,
                    "total_rows": 0,
                    "created_at": d.created_at,
                }
                for d in destinations
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("")
async def create_destination(
    req: DestinationCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
):
    repo = DestinationRepository(db)
    data = req.model_dump()
    if "password" in data:
        data["password_enc"] = encrypt_password(data.pop("password"))
    dest = repo.create(data)
    return {"status": "ok", "data": {"id": str(dest.id)}}


@router.get("/{dest_id}")
async def get_destination(
    dest_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    repo = DestinationRepository(db)
    dest = repo.get_by_id(dest_id)
    if not dest:
        raise NotFoundError(f"Destination {dest_id} not found")
    return {
        "status": "ok",
        "data": {
            "id": str(dest.id),
            "name": dest.name,
            "type": dest.type,
            "host": dest.host,
            "port": dest.port,
            "database": dest.database,
            "username": dest.username,
            "raw_schema": dest.raw_schema,
            "target_schema": dest.target_schema,
            "is_default": dest.is_default,
            "status": dest.status,
            "created_at": dest.created_at,
        },
    }


@router.put("/{dest_id}")
async def update_destination(
    dest_id: str,
    req: DestinationUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
):
    repo = DestinationRepository(db)
    dest = repo.get_by_id(dest_id)
    if not dest:
        raise NotFoundError(f"Destination {dest_id} not found")
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if "password" in data:
        data["password_enc"] = encrypt_password(data.pop("password"))
    repo.update(dest, data)
    return {"status": "ok", "data": {"updated": True}}


@router.delete("/{dest_id}")
async def delete_destination(
    dest_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
):
    repo = DestinationRepository(db)
    dest = repo.get_by_id(dest_id)
    if not dest:
        raise NotFoundError(f"Destination {dest_id} not found")
    repo.delete(dest)
    return {"status": "ok", "data": {"deleted": True}}


@router.post("/{dest_id}/test")
async def test_destination(
    dest_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
):
    from arus.shared.crypto import decrypt_password
    from arus.modules.connector.registry import get_destination

    repo = DestinationRepository(db)
    dest = repo.get_by_id(dest_id)
    if not dest:
        raise NotFoundError(f"Destination {dest_id} not found")

    try:
        conn_class = get_destination(dest.type)
        conn = conn_class()
        conn.connect({
            "host": dest.host,
            "port": dest.port,
            "username": dest.username,
            "password": decrypt_password(dest.password_enc),
            "database": dest.database,
        })
        ok = conn.test_connection()
        return {"status": "ok", "data": {"connected": ok}}
    except Exception as e:
        return {"status": "ok", "data": {"connected": False, "error": str(e)}}

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.crypto import encrypt_password
from arus.shared.exceptions import NotFoundError
from arus.modules.source.schemas import SourceCreate, SourceUpdate, TablesUpdate
from arus.modules.source.repository import SourceRepository
from arus.modules.source.service import SourceService
from arus.modules.auth.router import get_current_user
from arus.modules.destination.repository import DestinationRepository

router = APIRouter(prefix="/api/sources", tags=["sources"])


def get_source_service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(SourceRepository(db))


@router.get("")
async def list_sources(
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    sources = service.repo.list_all()
    return {
        "status": "ok",
        "data": [
            {
                "id": str(s.id),
                "name": s.name,
                "type": s.type,
                "host": s.host,
                "port": s.port,
                "database": s.database,
                "uri": s.uri,
                "auth_source": s.auth_source,
                "status": s.status,
                "table_count": 0,
                "enabled_table_count": 0,
                "last_tested": s.last_tested,
                "created_at": s.created_at,
            }
            for s in sources
        ],
    }


@router.post("")
async def create_source(
    req: SourceCreate,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    data = req.model_dump()
    data["password_enc"] = encrypt_password(data.pop("password"))
    source = service.repo.create(data)
    return {"status": "ok", "data": {"id": str(source.id)}}


@router.get("/{source_id}")
async def get_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    source = service.repo.get_by_id(source_id)
    if not source:
        raise NotFoundError(f"Source {source_id} not found")
    return {
        "status": "ok",
        "data": {
            "id": str(source.id),
            "name": source.name,
            "type": source.type,
            "host": source.host,
            "port": source.port,
            "database": source.database,
            "uri": source.uri,
            "auth_source": source.auth_source,
            "username": source.username,
            "ssl": source.ssl,
            "sync_method": source.sync_method,
            "table_include": source.table_include,
            "table_exclude": source.table_exclude,
            "status": source.status,
            "last_tested": source.last_tested,
            "created_at": source.created_at,
        },
    }


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    req: SourceUpdate,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    source = service.repo.get_by_id(source_id)
    if not source:
        raise NotFoundError(f"Source {source_id} not found")
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if "password" in data:
        data["password_enc"] = encrypt_password(data.pop("password"))
    service.repo.update(source, data)
    return {"status": "ok", "data": {"updated": True}}


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    source = service.repo.get_by_id(source_id)
    if not source:
        raise NotFoundError(f"Source {source_id} not found")
    service.repo.delete(source)
    return {"status": "ok", "data": {"deleted": True}}


@router.post("/{source_id}/test")
async def test_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    result = service.test_connection(source_id)
    return {"status": "ok", "data": result}


@router.post("/{source_id}/discover")
async def discover_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    tables = service.discover_tables(source_id)
    return {"status": "ok", "data": {"source_id": source_id, "tables": tables}}


@router.put("/{source_id}/tables")
async def update_source_tables(
    source_id: str,
    req: TablesUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update table selection for a source and auto-create/update the pipeline."""
    from arus.modules.pipeline.service import PipelineService
    from arus.modules.pipeline.repository import PipelineRepository

    dest_repo = DestinationRepository(db)
    default_dest = dest_repo.get_default()
    if not default_dest:
        raise NotFoundError("No default destination configured. Please add a destination first.")

    pipe_service = PipelineService(PipelineRepository(db), db)
    result = pipe_service.auto_create_from_source(source_id, str(default_dest.id), req.tables)
    return {"status": "ok", "data": result}

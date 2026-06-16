from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.crypto import encrypt_password
from arus.shared.exceptions import NotFoundError
from arus.modules.source.schemas import SourceCreate, SourceUpdate, TablesUpdate
from arus.modules.source.repository import SourceRepository
from arus.modules.source.service import SourceService
from arus.modules.auth.router import get_current_user, require_editor_or_admin
from arus.modules.destination.repository import DestinationRepository

router = APIRouter(prefix="/api/sources", tags=["sources"])


def get_source_service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(SourceRepository(db))


@router.get("")
async def list_sources(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(get_current_user),
):
    sources = service.repo.list_all(limit=limit, offset=offset)
    total = service.repo.count_all()
    return {
        "status": "ok",
        "data": {
            "sources": [
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
                    "table_count": s.table_count or 0,
                    "enabled_table_count": s.enabled_table_count or 0,
                    "schema_include": s.schema_include or [],
                    "last_tested": s.last_tested,
                    "created_at": s.created_at,
                }
                for s in sources
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }

@router.post("")
async def create_source(
    req: SourceCreate,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(require_editor_or_admin),
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
            "schema_include": source.schema_include or [],
            "table_count": source.table_count or 0,
            "enabled_table_count": source.enabled_table_count or 0,
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
    user: dict = Depends(require_editor_or_admin),
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
    user: dict = Depends(require_editor_or_admin),
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
    user: dict = Depends(require_editor_or_admin),
):
    result = service.test_connection(source_id)
    return {"status": "ok", "data": result}


@router.post("/{source_id}/discover")
async def discover_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(require_editor_or_admin),
):
    tables = service.discover_tables(source_id)
    return {"status": "ok", "data": {"source_id": source_id, "tables": tables}}


@router.post("/{source_id}/schemas")
async def discover_source_schemas(
    source_id: str,
    service: SourceService = Depends(get_source_service),
    user: dict = Depends(require_editor_or_admin),
):
    """Discover available schemas in the source database."""
    schemas = service.discover_schemas(source_id)
    return {"status": "ok", "data": {"source_id": source_id, "schemas": schemas}}


@router.put("/{source_id}/tables")
async def update_source_tables(
    source_id: str,
    req: TablesUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
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

    # Update source table counts after saving selection
    source_repo = SourceRepository(db)
    source = source_repo.get_by_id(source_id)
    if source:
        enabled = sum(1 for t in req.tables if t.get("enabled", True))
        source.table_count = len(req.tables)
        source.enabled_table_count = enabled
        source.status = "connected"
        db.commit()

    return {"status": "ok", "data": result}

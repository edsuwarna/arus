from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import NotFoundError
from arus.modules.auth.router import get_current_user, require_editor_or_admin
from arus.modules.notification.schemas import (
    NotificationTargetCreate,
    NotificationTargetUpdate,
    PipelineNotificationCreate,
    PipelineNotificationUpdate,
    TestNotificationRequest,
)
from arus.modules.notification.repository import NotificationRepository
from arus.modules.notification.service import SENDERS
from arus.modules.notification.templates import BUILDERS

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def get_repo(db: Session = Depends(get_db)):
    return NotificationRepository(db)


# -- NotificationTarget CRUD --

@router.get("/targets")
async def list_targets(
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(get_current_user),
):
    targets = repo.list_targets()
    return {"status": "ok", "data": targets}


@router.post("/targets")
async def create_target(
    req: NotificationTargetCreate,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    if req.type not in SENDERS:
        return {"status": "error", "error": {"message": f"Unsupported type: {req.type}. Supported: {list(SENDERS.keys())}"}}
    result = repo.create_target(req.model_dump())
    return {"status": "ok", "data": result}


@router.put("/targets/{target_id}")
async def update_target(
    target_id: str,
    req: NotificationTargetUpdate,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    result = repo.update_target(target_id, data)
    if not result:
        raise NotFoundError(f"Notification target {target_id} not found")
    return {"status": "ok", "data": result}


@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: str,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    deleted = repo.delete_target(target_id)
    if not deleted:
        raise NotFoundError(f"Notification target {target_id} not found")
    return {"status": "ok", "data": {"deleted": True}}


@router.post("/targets/{target_id}/test")
async def test_target(
    target_id: str,
    req: TestNotificationRequest,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(get_current_user),
):
    target = repo.get_target(target_id)
    if not target:
        raise NotFoundError(f"Notification target {target_id} not found")

    sender = SENDERS.get(target["type"])
    if not sender:
        return {"status": "error", "error": {"message": f"No sender for type: {target['type']}"}}

    # Build message from template if event_type is specified
    event_type = req.event_type or "test"
    builder = BUILDERS.get(event_type)
    if not builder:
        return {"status": "error", "error": {"message": f"Unknown event_type: {event_type}"}}

    data = builder()

    success = sender(target["config"], data)
    if success:
        return {"status": "ok", "data": {"sent": True, "type": target["type"], "target": target["name"], "event_type": event_type}}
    else:
        return {"status": "error", "error": {"message": f"Failed to send {event_type} notification to {target['name']} ({target['type']})"}}

# -- PipelineNotification links --

@router.get("/links/{pipeline_id}")
async def list_pipeline_links(
    pipeline_id: str,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(get_current_user),
):
    links = repo.list_by_pipeline(pipeline_id)
    # Enrich with target info
    result = []
    for link in links:
        target = repo.get_target(link["target_id"])
        result.append({
            "id": link["id"],
            "pipeline_id": link["pipeline_id"],
            "target_id": link["target_id"],
            "target_name": target["name"] if target else "",
            "target_type": target["type"] if target else "",
            "event_types": list(link["event_types"]) if link.get("event_types") else [],
            "created_at": link["created_at"].isoformat() if hasattr(link["created_at"], "isoformat") else link.get("created_at"),
        })
    return {"status": "ok", "data": result}


@router.post("/links")
async def create_pipeline_link(
    req: PipelineNotificationCreate,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    result = repo.create_pipeline_notification(req.model_dump())
    # Enrich with target info
    target = repo.get_target(result["target_id"])
    result["target_name"] = target["name"] if target else ""
    result["target_type"] = target["type"] if target else ""
    return {"status": "ok", "data": result}


@router.put("/links/{link_id}")
async def update_pipeline_link(
    link_id: str,
    req: PipelineNotificationUpdate,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    result = repo.update_pipeline_notification(link_id, data)
    if not result:
        raise NotFoundError(f"Pipeline notification link {link_id} not found")
    return {"status": "ok", "data": result}


@router.delete("/links/{link_id}")
async def delete_pipeline_link(
    link_id: str,
    repo: NotificationRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    deleted = repo.delete_pipeline_notification(link_id)
    if not deleted:
        raise NotFoundError(f"Pipeline notification link {link_id} not found")
    return {"status": "ok", "data": {"deleted": True}}

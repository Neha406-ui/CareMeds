import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.operations import AuditLog


def record_audit(
    db: Session,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None,
    details: dict | None = None,
) -> None:
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=json.dumps(details, separators=(",", ":"), sort_keys=True) if details else None,
    ))

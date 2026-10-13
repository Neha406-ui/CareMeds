from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.operations import AuditLog, InventoryBatch, InventoryTransaction
from app.models.prescription import Medicine
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas import InventoryStockIn, InventoryStockOut
from app.services.audit import record_audit

router = APIRouter()
INVENTORY_ROLES = (UserRole.ADMIN.value, UserRole.DOCTOR.value, UserRole.CARETAKER.value)
INVENTORY_EDIT_ROLES = (UserRole.ADMIN.value, UserRole.CARETAKER.value)


@router.get("/inventory", dependencies=[Depends(require_role(*INVENTORY_ROLES))])
def list_inventory(
    expiring_within_days: int = Query(default=30, ge=0, le=3650),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()
    medicines = db.query(Medicine).filter(Medicine.is_active.is_(True)).order_by(Medicine.name).all()
    by_medicine = {
        str(medicine.id): {
            "medicine_id": str(medicine.id),
            "medicine_name": medicine.name,
            "reorder_level": medicine.reorder_level,
            "total_quantity": 0,
            "available_quantity": 0,
            "low_stock": medicine.reorder_level >= 0,
            "batches": [],
        }
        for medicine in medicines
    }
    batches = db.query(InventoryBatch).join(Medicine).filter(
        Medicine.is_active.is_(True)
    ).order_by(InventoryBatch.expires_on).all()
    for batch in batches:
        entry = by_medicine.get(str(batch.medicine_id))
        if entry is None:
            continue
        entry["total_quantity"] += batch.quantity_remaining
        if batch.expires_on >= today:
            entry["available_quantity"] += batch.quantity_remaining
        entry["batches"].append({
            "id": str(batch.id),
            "lot_code": batch.lot_code,
            "expires_on": batch.expires_on,
            "quantity_remaining": batch.quantity_remaining,
            "expired": batch.expires_on < today,
            "expiring_soon": today <= batch.expires_on <= date.fromordinal(today.toordinal() + expiring_within_days),
        })
    for entry in by_medicine.values():
        entry["low_stock"] = entry["available_quantity"] <= entry["reorder_level"]
    return list(by_medicine.values())


@router.post(
    "/inventory/stock-in",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*INVENTORY_EDIT_ROLES))],
)
def stock_in(
    item: InventoryStockIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    medicine = db.query(Medicine).filter(
        Medicine.id == item.medicine_id,
        Medicine.is_active.is_(True),
    ).first()
    if medicine is None:
        raise HTTPException(status_code=404, detail="Active medicine not found")
    if item.expires_on < datetime.now(timezone.utc).date():
        raise HTTPException(status_code=409, detail="Expired medicine cannot be received")
    batch = db.query(InventoryBatch).filter_by(
        medicine_id=item.medicine_id,
        lot_code=item.lot_code.strip(),
    ).with_for_update().first()
    if batch is not None and batch.expires_on != item.expires_on:
        raise HTTPException(status_code=409, detail="Lot code already exists with another expiry date")
    if batch is None:
        batch = InventoryBatch(
            medicine_id=item.medicine_id,
            lot_code=item.lot_code.strip(),
            expires_on=item.expires_on,
            quantity_remaining=0,
        )
        db.add(batch)
        db.flush()
    batch.quantity_remaining += item.quantity
    db.add(InventoryTransaction(
        batch_id=batch.id,
        actor_id=current_user.id,
        transaction_type="stock_in",
        quantity=item.quantity,
        quantity_after=batch.quantity_remaining,
        reason=item.reason.strip() if item.reason else None,
    ))
    record_audit(
        db,
        current_user.id,
        "inventory_stock_in",
        "inventory_batch",
        batch.id,
        {"quantity": item.quantity, "quantity_after": batch.quantity_remaining},
    )
    db.commit()
    return {
        "batch_id": str(batch.id),
        "medicine_id": str(medicine.id),
        "quantity_remaining": batch.quantity_remaining,
        "expires_on": batch.expires_on,
    }


@router.post(
    "/inventory/batches/{batch_id}/stock-out",
    dependencies=[Depends(require_role(*INVENTORY_EDIT_ROLES))],
)
def stock_out(
    batch_id: UUID,
    item: InventoryStockOut,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.query(InventoryBatch).filter(
        InventoryBatch.id == batch_id
    ).with_for_update().first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Inventory batch not found")
    if batch.expires_on < datetime.now(timezone.utc).date():
        raise HTTPException(status_code=409, detail="Expired medicine cannot be issued")
    medicine = db.query(Medicine.id).filter(
        Medicine.id == batch.medicine_id,
        Medicine.is_active.is_(True),
    ).first()
    if medicine is None:
        raise HTTPException(status_code=409, detail="Inactive medicine cannot be issued")
    if batch.quantity_remaining < item.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    batch.quantity_remaining -= item.quantity
    db.add(InventoryTransaction(
        batch_id=batch.id,
        actor_id=current_user.id,
        transaction_type="stock_out",
        quantity=item.quantity,
        quantity_after=batch.quantity_remaining,
        reason=item.reason.strip(),
    ))
    record_audit(
        db,
        current_user.id,
        "inventory_stock_out",
        "inventory_batch",
        batch.id,
        {"quantity": item.quantity, "quantity_after": batch.quantity_remaining},
    )
    db.commit()
    return {"batch_id": str(batch.id), "quantity_remaining": batch.quantity_remaining}


@router.get(
    "/inventory/transactions",
    dependencies=[Depends(require_role(*INVENTORY_ROLES))],
)
def inventory_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": str(transaction.id),
            "batch_id": str(transaction.batch_id),
            "transaction_type": transaction.transaction_type,
            "quantity": transaction.quantity,
            "quantity_after": transaction.quantity_after,
            "reason": transaction.reason,
            "actor_id": str(transaction.actor_id),
            "occurred_at": transaction.occurred_at,
        }
        for transaction in db.query(InventoryTransaction).order_by(
            InventoryTransaction.occurred_at.desc()
        ).limit(limit).all()
    ]


@router.get(
    "/audit-logs",
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": str(entry.id),
            "actor_id": str(entry.actor_id) if entry.actor_id else None,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": entry.details,
            "occurred_at": entry.occurred_at,
        }
        for entry in db.query(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit).all()
    ]

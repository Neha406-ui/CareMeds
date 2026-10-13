from datetime import date, datetime, timedelta, timezone
import json
import secrets
from uuid import uuid4

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.family import FamilyLink
from app.models.operations import AuditLog
from app.models.prescription import Medicine, Prescription, PrescriptionHistory, PrescriptionStatus
from app.models.resident import Resident
from app.models.user import User, UserRole


def make_user(db, role, username=None, is_active=True):
    user = User(
        id=uuid4(),
        username=username or f"{role.value}-{uuid4().hex[:8]}",
        password_hash=get_password_hash("test-password-123"),
        role=role,
        full_name=role.value.replace("_", " ").title(),
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def auth_headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user.username, 'ver': user.token_version})}"}


@pytest.fixture
def care_data(db_session):
    db = db_session
    admin = make_user(db, UserRole.ADMIN, "admin")
    doctor = make_user(db, UserRole.DOCTOR, "doctor")
    other_doctor = make_user(db, UserRole.DOCTOR, "other-doctor")
    caretaker = make_user(db, UserRole.CARETAKER, "caretaker")
    resident_user = make_user(db, UserRole.RESIDENT, "resident")
    other_resident_user = make_user(db, UserRole.RESIDENT, "other-resident")
    family = make_user(db, UserRole.FAMILY_MEMBER, "family")

    resident = Resident(id=uuid4(), user_id=resident_user.id, full_name="Resident One", is_active=True)
    other_resident = Resident(id=uuid4(), user_id=other_resident_user.id, full_name="Resident Two", is_active=True)
    db.add_all([resident, other_resident])
    db.flush()

    db.add_all([
        DoctorAssignment(doctor_id=doctor.id, resident_id=resident.id, assigned_by=admin.id, is_active=True),
        DoctorAssignment(doctor_id=other_doctor.id, resident_id=resident.id, assigned_by=admin.id, is_active=True),
        CaretakerAssignment(caretaker_id=caretaker.id, resident_id=resident.id, assigned_by=admin.id, is_active=True),
        FamilyLink(
            resident_id=resident.id,
            family_member_id=family.id,
            consent_granted=True,
            can_view_profile=True,
            can_view_prescriptions=True,
            consent_granted_at=datetime.utcnow(),
            consent_granted_by=resident_user.id,
            is_active=True,
        ),
    ])
    medicine = Medicine(id=uuid4(), name="Medication", is_active=True)
    db.add(medicine)
    db.flush()
    prescription = Prescription(
        id=uuid4(),
        resident_id=resident.id,
        doctor_id=doctor.id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        frequency="Daily",
        scheduled_times=["09:00"],
        start_date=date.today(),
        status=PrescriptionStatus.ACTIVE,
    )
    other_prescription = Prescription(
        id=uuid4(),
        resident_id=other_resident.id,
        doctor_id=doctor.id,
        medicine_id=medicine.id,
        dosage="2 tablets",
        frequency="Twice daily",
        scheduled_times=["09:00", "21:00"],
        start_date=date.today(),
        status=PrescriptionStatus.ACTIVE,
    )
    db.add_all([prescription, other_prescription])
    db.commit()
    return {
        "admin": admin,
        "doctor": doctor,
        "other_doctor": other_doctor,
        "caretaker": caretaker,
        "resident": resident_user,
        "other_resident": other_resident_user,
        "family": family,
        "resident_record": resident,
        "other_resident_record": other_resident,
        "medicine": medicine,
        "prescription": prescription,
        "other_prescription": other_prescription,
    }


def test_resident_routes_are_scoped_to_ownership_assignment_or_consent(test_client, care_data):
    data = care_data
    expected = {
        "admin": {data["resident_record"].id, data["other_resident_record"].id},
        "doctor": {data["resident_record"].id},
        "other_doctor": {data["resident_record"].id},
        "caretaker": {data["resident_record"].id},
        "resident": {data["resident_record"].id},
        "other_resident": {data["other_resident_record"].id},
        "family": {data["resident_record"].id},
    }
    for role, user in data.items():
        if role not in expected:
            continue
        headers = auth_headers(user)
        listed = test_client.get("/api/residents", headers=headers)
        assert listed.status_code == 200
        assert {item["id"] for item in listed.json()} == {str(value) for value in expected[role]}
        for resident_id in (data["resident_record"].id, data["other_resident_record"].id):
            response = test_client.get(f"/api/residents/{resident_id}", headers=headers)
            if resident_id in expected[role]:
                assert response.status_code == 200
            else:
                assert response.status_code == 404


def test_prescription_lists_follow_resident_access_scope(test_client, care_data):
    data = care_data
    expected = {
        "admin": {data["prescription"].id, data["other_prescription"].id},
        "doctor": {data["prescription"].id},
        "other_doctor": {data["prescription"].id},
        "caretaker": {data["prescription"].id},
        "resident": {data["prescription"].id},
        "other_resident": {data["other_prescription"].id},
        "family": {data["prescription"].id},
    }
    for role, user in data.items():
        if role not in expected:
            continue
        response = test_client.get("/api/prescriptions", headers=auth_headers(user))
        assert response.status_code == 200
        assert {item["id"] for item in response.json()} == {str(value) for value in expected[role]}


def test_schedule_generation_is_idempotent_scoped_and_auditable(test_client, care_data):
    data = care_data
    yesterday = date.today() - timedelta(days=1)
    data["prescription"].start_date = yesterday
    data["prescription"].scheduled_times = ["09:00", "21:00"]
    data["prescription"].timezone = "UTC"
    first = test_client.get(
        f"/api/doses?start_date={yesterday.isoformat()}",
        headers=auth_headers(data["admin"]),
    )
    assert first.status_code == 200
    first_resident_doses = [dose for dose in first.json() if dose["resident_id"] == str(data["resident_record"].id)]
    assert [dose["scheduled_local_time"] for dose in first_resident_doses] == ["09:00", "21:00"]

    repeated = test_client.get(
        f"/api/doses?start_date={yesterday.isoformat()}",
        headers=auth_headers(data["admin"]),
    )
    assert repeated.status_code == 200
    repeated_doses = [dose for dose in repeated.json() if dose["resident_id"] == str(data["resident_record"].id)]
    assert [dose["id"] for dose in repeated_doses] == [dose["id"] for dose in first_resident_doses]

    caretaker_headers = auth_headers(data["caretaker"])
    scoped = test_client.get(
        f"/api/doses?start_date={yesterday.isoformat()}",
        headers=caretaker_headers,
    )
    assert {dose["resident_id"] for dose in scoped.json()} == {str(data["resident_record"].id)}
    assert test_client.get(
        f"/api/doses?start_date={yesterday.isoformat()}&end_date={(yesterday + timedelta(days=31)).isoformat()}",
        headers=caretaker_headers,
    ).status_code == 400

    dose_id = first_resident_doses[0]["id"]
    assert test_client.post(
        f"/api/doses/{dose_id}/outcome",
        headers=auth_headers(data["doctor"]),
        json={"status": "administered"},
    ).status_code == 403
    acknowledged = test_client.post(
        f"/api/doses/{dose_id}/acknowledge",
        headers=auth_headers(data["resident"]),
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "scheduled"
    assert acknowledged.json()["acknowledged_at"] is not None

    outcome = test_client.post(
        f"/api/doses/{dose_id}/outcome",
        headers=caretaker_headers,
        json={"status": "refused", "reason": "Resident declined"},
    )
    assert outcome.status_code == 200
    assert outcome.json()["status"] == "refused"
    assert outcome.json()["actual_at"] is None
    assert test_client.post(
        f"/api/doses/{dose_id}/outcome",
        headers=caretaker_headers,
        json={"status": "administered"},
    ).status_code == 409
    history = test_client.get(
        f"/api/doses/{dose_id}/history",
        headers=auth_headers(data["doctor"]),
    )
    assert history.status_code == 200
    assert {event["event_type"] for event in history.json()} == {
        "reminder_acknowledged",
        "outcome_recorded",
    }


def test_schedule_access_follows_family_prescription_permission(test_client, care_data, db_session):
    data = care_data
    target_day = date.today().isoformat()
    headers = auth_headers(data["family"])
    assert test_client.get(f"/api/doses?start_date={target_day}", headers=headers).status_code == 200
    link = db_session.query(FamilyLink).filter_by(
        resident_id=data["resident_record"].id,
        family_member_id=data["family"].id,
    ).one()
    link.can_view_prescriptions = False
    db_session.commit()
    denied = test_client.get(f"/api/doses?start_date={target_day}", headers=headers)
    assert denied.status_code == 200
    assert denied.json() == []


def test_prescription_revision_cancels_pending_doses_and_generates_new_schedule(test_client, care_data):
    data = care_data
    tomorrow = date.today() + timedelta(days=1)
    headers = auth_headers(data["admin"])
    generated = test_client.get(
        f"/api/doses?start_date={tomorrow.isoformat()}",
        headers=headers,
    )
    assert generated.status_code == 200
    previous = next(
        dose for dose in generated.json()
        if dose["prescription_id"] == str(data["prescription"].id)
    )
    updated = test_client.put(
        f"/api/prescriptions/{data['prescription'].id}",
        headers=auth_headers(data["doctor"]),
        json={"scheduled_times": ["10:30"]},
    )
    assert updated.status_code == 200
    refreshed = test_client.get(
        f"/api/doses?start_date={tomorrow.isoformat()}",
        headers=headers,
    )
    assert refreshed.status_code == 200
    current = [
        dose for dose in refreshed.json()
        if dose["prescription_id"] == str(data["prescription"].id)
    ]
    assert [dose["scheduled_local_time"] for dose in current] == ["10:30"]
    events = test_client.get(
        f"/api/doses/{previous['id']}/history",
        headers=auth_headers(data["doctor"]),
    )
    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "schedule_cancelled"


def test_reminder_worker_is_idempotent_escalates_without_marking_missed(
    test_client, care_data, db_session,
):
    from app.models.dose import DoseOccurrence
    from app.services.reminders import run_reminder_cycle

    data = care_data
    today = date.today()
    data["prescription"].start_date = today
    data["prescription"].scheduled_times = ["09:00"]
    data["prescription"].timezone = "UTC"

    def run_at(hour, minute):
        return run_reminder_cycle(
            db_session,
            datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute),
        )

    upcoming = run_at(8, 50)
    assert upcoming["notifications_created"] > 0
    assert run_at(8, 51)["notifications_created"] == 0
    due = run_at(9, 1)
    assert due["notifications_created"] > 0
    overdue = run_at(10, 2)
    assert overdue["notifications_created"] > 0
    assert overdue["escalations_created"] > 0

    dose = db_session.query(DoseOccurrence).filter_by(
        prescription_id=data["prescription"].id,
        scheduled_date=today,
    ).one()
    assert dose.status == "scheduled"
    caretaker_headers = auth_headers(data["caretaker"])
    notifications = test_client.get("/api/notifications", headers=caretaker_headers)
    assert notifications.status_code == 200
    assert {item["notification_type"] for item in notifications.json()} == {
        "dose_upcoming",
        "dose_due",
        "dose_overdue",
    }
    family_notifications = test_client.get(
        "/api/notifications",
        headers=auth_headers(data["family"]),
    )
    assert family_notifications.status_code == 200
    assert family_notifications.json()

    escalations = test_client.get("/api/escalations", headers=caretaker_headers)
    assert escalations.status_code == 200
    escalation = escalations.json()[0]
    resolved = test_client.post(
        f"/api/escalations/{escalation['id']}/resolve",
        headers=caretaker_headers,
        json={"notes": "Checked with resident"},
    )
    assert resolved.status_code == 200
    assert test_client.get("/api/escalations", headers=caretaker_headers).json() == []

    link = db_session.query(FamilyLink).filter_by(
        resident_id=data["resident_record"].id,
        family_member_id=data["family"].id,
    ).one()
    link.can_view_prescriptions = False
    db_session.commit()
    assert test_client.get(
        "/api/notifications",
        headers=auth_headers(data["family"]),
    ).json() == []


def test_inventory_transactions_enforce_roles_expiry_and_nonnegative_stock(test_client, care_data):
    data = care_data
    admin_headers = auth_headers(data["admin"])
    caretaker_headers = auth_headers(data["caretaker"])
    medicine_response = test_client.post(
        "/api/medicines",
        headers=admin_headers,
        json={"name": "Stock test medicine", "reorder_level": 7},
    )
    assert medicine_response.status_code == 201
    medicine_id = medicine_response.json()["id"]
    stock_in = test_client.post(
        "/api/inventory/stock-in",
        headers=caretaker_headers,
        json={
            "medicine_id": medicine_id,
            "lot_code": "LOT-001",
            "expires_on": (date.today() + timedelta(days=20)).isoformat(),
            "quantity": 10,
            "reason": "Initial count",
        },
    )
    assert stock_in.status_code == 201
    batch_id = stock_in.json()["batch_id"]
    assert test_client.get("/api/inventory", headers=auth_headers(data["doctor"])).json()[-1]["total_quantity"] == 10
    assert test_client.post(
        f"/api/inventory/batches/{batch_id}/stock-out",
        headers=caretaker_headers,
        json={"quantity": 4, "reason": "Dispensed to unit"},
    ).json()["quantity_remaining"] == 6
    inventory = test_client.get("/api/inventory", headers=auth_headers(data["admin"])).json()
    batch_item = next(item for item in inventory if item["medicine_id"] == medicine_id)
    assert batch_item["total_quantity"] == 6
    assert batch_item["low_stock"] is True
    assert batch_item["batches"][0]["expiring_soon"] is True
    assert test_client.post(
        f"/api/inventory/batches/{batch_id}/stock-out",
        headers=caretaker_headers,
        json={"quantity": 7, "reason": "Overdraw attempt"},
    ).status_code == 409
    for role in ("admin", "doctor", "caretaker"):
        assert test_client.get("/api/inventory", headers=auth_headers(data[role])).status_code == 200
    for role in ("resident", "family"):
        assert test_client.get("/api/inventory", headers=auth_headers(data[role])).status_code == 403
    assert test_client.post(
        "/api/inventory/stock-in",
        headers=auth_headers(data["doctor"]),
        json={
            "medicine_id": medicine_id,
            "lot_code": "DOCTOR-CANNOT-RECEIVE",
            "expires_on": (date.today() + timedelta(days=20)).isoformat(),
            "quantity": 1,
        },
    ).status_code == 403
    assert test_client.post(
        "/api/inventory/stock-in",
        headers=auth_headers(data["resident"]),
        json={
            "medicine_id": medicine_id,
            "lot_code": "LOT-002",
            "expires_on": (date.today() + timedelta(days=20)).isoformat(),
            "quantity": 1,
        },
    ).status_code == 403
    assert test_client.get("/api/inventory/transactions", headers=auth_headers(data["admin"])).status_code == 200
    audit = test_client.get("/api/audit-logs", headers=admin_headers)
    assert audit.status_code == 200
    assert {entry["action"] for entry in audit.json()} >= {"inventory_stock_in", "inventory_stock_out"}
    assert test_client.get("/api/audit-logs", headers=auth_headers(data["doctor"])).status_code == 403


def test_family_contact_requests_require_linked_consent_and_assigned_staff(test_client, care_data, db_session):
    data = care_data
    family_headers = auth_headers(data["family"])
    resident_id = str(data["resident_record"].id)
    response = test_client.post(
        "/api/family-contact-requests",
        headers=family_headers,
        json={"resident_id": resident_id, "message": "Please call me about the care plan."},
    )
    assert response.status_code == 201
    request_id = response.json()["id"]
    assert test_client.get("/api/family-contact-requests", headers=family_headers).json()[0]["id"] == request_id
    assert test_client.get(
        "/api/family-contact-requests",
        headers=auth_headers(data["other_doctor"]),
    ).status_code == 200

    unassigned_doctor = make_user(db_session, UserRole.DOCTOR, "unassigned-contact-doctor")
    assert test_client.get(
        "/api/family-contact-requests",
        headers=auth_headers(unassigned_doctor),
    ).json() == []
    assert test_client.patch(
        f"/api/family-contact-requests/{request_id}",
        headers=auth_headers(unassigned_doctor),
        json={"status": "received", "response": "Received"},
    ).status_code == 404
    assert test_client.patch(
        f"/api/family-contact-requests/{request_id}",
        headers=family_headers,
        json={"status": "received", "response": "Family cannot respond to its own request."},
    ).status_code == 403
    assert test_client.patch(
        f"/api/family-contact-requests/{request_id}",
        headers=auth_headers(data["other_doctor"]),
        json={"status": "received", "response": "The assigned doctor received your request."},
    ).status_code == 200
    assert test_client.patch(
        f"/api/family-contact-requests/{request_id}",
        headers=auth_headers(data["caretaker"]),
        json={"status": "resolved", "response": "The care team resolved your request."},
    ).status_code == 200

    assert test_client.post(
        "/api/family-contact-requests",
        headers=family_headers,
        json={
            "resident_id": str(data["other_resident_record"].id),
            "message": "This resident has not linked this family account.",
        },
    ).status_code == 404
    assert test_client.delete(
        f"/api/residents/{resident_id}/family-consent/{data['family'].id}",
        headers=auth_headers(data["resident"]),
    ).status_code == 204
    assert test_client.get("/api/family-contact-requests", headers=family_headers).json() == []


def test_handovers_require_active_assignments_and_incoming_caretaker_acknowledgement(
    test_client, care_data, db_session
):
    data = care_data
    incoming = make_user(db_session, UserRole.CARETAKER, "incoming-caretaker")
    assignment = test_client.post(
        f"/api/residents/{data['resident_record'].id}/assignments/caretakers",
        headers=auth_headers(data["admin"]),
        json={"user_id": str(incoming.id)},
    )
    assert assignment.status_code == 201
    resident_id = str(data["resident_record"].id)
    start = datetime.now(timezone.utc).replace(microsecond=0)
    end = start + timedelta(hours=8)
    body = {
        "resident_id": resident_id,
        "incoming_caretaker_id": str(incoming.id),
        "shift_started_at": start.isoformat(),
        "shift_ended_at": end.isoformat(),
        "notes": "Routine handover notes.",
    }
    created = test_client.post(
        "/api/handovers",
        headers=auth_headers(data["caretaker"]),
        json=body,
    )
    assert created.status_code == 201
    handover_id = created.json()["id"]
    assert {item["id"] for item in test_client.get(
        "/api/handovers",
        headers=auth_headers(data["caretaker"]),
        params={"resident_id": resident_id},
    ).json()} == {handover_id}
    assert test_client.post(
        f"/api/handovers/{handover_id}/acknowledge",
        headers=auth_headers(data["caretaker"]),
    ).status_code == 404
    ack = test_client.post(
        f"/api/handovers/{handover_id}/acknowledge",
        headers=auth_headers(incoming),
    )
    assert ack.status_code == 200
    assert ack.json()["acknowledged_by"] == str(incoming.id)
    assert test_client.post(
        f"/api/handovers/{handover_id}/acknowledge",
        headers=auth_headers(incoming),
    ).status_code == 409

    outsider = make_user(db_session, UserRole.CARETAKER, "unassigned-handover-caretaker")
    body["incoming_caretaker_id"] = str(outsider.id)
    assert test_client.post(
        "/api/handovers",
        headers=auth_headers(data["caretaker"]),
        json=body,
    ).status_code == 409
    body["resident_id"] = str(data["other_resident_record"].id)
    body["incoming_caretaker_id"] = str(incoming.id)
    assert test_client.post(
        "/api/handovers",
        headers=auth_headers(data["caretaker"]),
        json=body,
    ).status_code == 404


def test_adherence_analytics_counts_unknown_states_and_scopes_residents(test_client, care_data, db_session):
    data = care_data
    yesterday = date.today() - timedelta(days=1)
    data["prescription"].start_date = yesterday
    data["other_prescription"].start_date = yesterday
    db_session.commit()
    start = yesterday.isoformat()
    scheduled = test_client.get(
        f"/api/doses?start_date={start}&end_date={start}",
        headers=auth_headers(data["admin"]),
    )
    assert scheduled.status_code == 200
    resident_doses = [
        dose for dose in scheduled.json()
        if dose["resident_id"] == str(data["resident_record"].id)
    ]
    assert len(resident_doses) == 1
    outcome = test_client.post(
        f"/api/doses/{resident_doses[0]['id']}/outcome",
        headers=auth_headers(data["caretaker"]),
        json={"status": "administered"},
    )
    assert outcome.status_code == 200

    expected = {
        "admin": (3, 1),
        "doctor": (1, 1),
        "caretaker": (1, 1),
        "resident": (1, 1),
        "other_resident": (2, 0),
        "family": (1, 1),
    }
    for role, (total, administered) in expected.items():
        report_response = test_client.get(
            f"/api/analytics/adherence?start_date={start}&end_date={start}",
            headers=auth_headers(data[role]),
        )
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["total_doses"] == total
        assert report["counts"]["administered"] == administered
        assert report["counts"]["unresolved"] == total - administered
        assert report["adherence_rate_percent"] == round(administered / total * 100, 2)
        expected_residents = (
            {str(data["resident_record"].id), str(data["other_resident_record"].id)}
            if role == "admin"
            else {str(data["other_resident_record"].id)}
            if role == "other_resident"
            else {str(data["resident_record"].id)}
        )
        assert set(report["per_resident"]) == expected_residents

    link = db_session.query(FamilyLink).filter_by(
        resident_id=data["resident_record"].id,
        family_member_id=data["family"].id,
    ).one()
    link.can_view_profile = False
    db_session.commit()
    family_report = test_client.get(
        f"/api/analytics/adherence?start_date={start}&end_date={start}",
        headers=auth_headers(data["family"]),
    ).json()
    assert family_report["per_resident"][str(data["resident_record"].id)]["resident_name"] is None


def test_deactivated_resident_dose_cannot_be_changed_by_stale_assignment(test_client, care_data, db_session):
    data = care_data
    yesterday = date.today() - timedelta(days=1)
    data["prescription"].start_date = yesterday
    db_session.commit()
    doses = test_client.get(
        f"/api/doses?start_date={yesterday.isoformat()}&end_date={yesterday.isoformat()}",
        headers=auth_headers(data["admin"]),
    ).json()
    dose = next(item for item in doses if item["resident_id"] == str(data["resident_record"].id))
    data["resident_record"].is_active = False
    db_session.commit()
    response = test_client.post(
        f"/api/doses/{dose['id']}/outcome",
        headers=auth_headers(data["caretaker"]),
        json={"status": "administered"},
    )
    assert response.status_code == 404


def test_all_protected_routes_reject_anonymous_requests(test_client, care_data):
    resident_id = care_data["resident_record"].id
    prescription_id = care_data["prescription"].id
    protected_requests = [
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/auth/users"),
        ("POST", "/api/auth/users"),
        ("PATCH", f"/api/auth/users/{care_data['admin'].id}"),
        ("GET", "/api/users"),
        ("POST", "/api/residents"),
        ("GET", "/api/residents"),
        ("GET", f"/api/residents/{resident_id}"),
        ("PUT", f"/api/residents/{resident_id}"),
        ("DELETE", f"/api/residents/{resident_id}"),
        ("GET", "/api/assignments"),
        ("POST", f"/api/family-links/{resident_id}"),
        ("GET", f"/api/residents/{resident_id}/family-consents"),
        ("GET", "/api/family-links"),
        ("DELETE", f"/api/family-links/{resident_id}"),
        ("POST", f"/api/residents/{resident_id}/family-consent"),
        ("DELETE", f"/api/residents/{resident_id}/family-consent/{uuid4()}"),
        ("POST", f"/api/residents/{resident_id}/assignments/doctors"),
        ("POST", f"/api/residents/{resident_id}/assignments/caretakers"),
        ("GET", "/api/medicines"),
        ("POST", "/api/medicines"),
        ("GET", "/api/prescriptions"),
        ("GET", "/api/doses"),
        ("GET", "/api/notifications"),
        ("GET", "/api/inventory"),
        ("GET", "/api/audit-logs"),
        ("GET", "/api/analytics/adherence"),
        ("POST", "/api/prescriptions"),
        ("PUT", f"/api/prescriptions/{prescription_id}"),
        ("POST", f"/api/prescriptions/{prescription_id}/discontinue"),
    ]
    for method, path in protected_requests:
        response = test_client.request(method, path)
        assert response.status_code == 401, (method, path, response.text)


def test_administrative_mutations_are_admin_only(test_client, care_data):
    data = care_data
    resident_id = data["resident_record"].id
    assignment_path = f"/api/residents/{resident_id}/assignments/doctors"
    for role in ("doctor", "other_doctor", "caretaker", "resident", "other_resident", "family"):
        headers = auth_headers(data[role])
        assert test_client.get("/api/auth/users", headers=headers).status_code == 403
        assert test_client.get("/api/assignments", headers=headers).status_code == 403
        assert test_client.post("/api/auth/users", headers=headers, json={
            "username": "new-account", "password": "test-password-123", "role": "resident",
        }).status_code == 403
        assert test_client.patch(
            f"/api/auth/users/{data['doctor'].id}",
            headers=headers,
            json={"is_active": False},
        ).status_code == 403
        assert test_client.post("/api/residents", headers=headers, json={"full_name": "New Resident"}).status_code == 403
        assert test_client.put(f"/api/residents/{resident_id}", headers=headers, json={"full_name": "Changed"}).status_code == 403
        assert test_client.delete(f"/api/residents/{resident_id}", headers=headers).status_code == 403
        assert test_client.post(assignment_path, headers=headers, json={"user_id": str(data["doctor"].id)}).status_code == 403
    assert test_client.get("/api/auth/users", headers=auth_headers(data["admin"])).status_code == 200
    assert test_client.get("/api/assignments", headers=auth_headers(data["admin"])).status_code == 200


def test_admin_can_create_accounts_for_all_roles_but_others_cannot(test_client, care_data, db_session):
    data = care_data
    payload = {
        "username": "new-caretaker",
        "password": "new-secure-password-123",
        "full_name": "New Caretaker",
        "phone": "555-0100",
        "role": "caretaker",
    }
    for role in ("doctor", "caretaker", "resident", "family"):
        response = test_client.post(
            "/api/auth/users",
            headers=auth_headers(data[role]),
            json={**payload, "username": f"{role}-cannot-register"},
        )
        assert response.status_code == 403

    created = test_client.post(
        "/api/auth/users",
        headers=auth_headers(data["admin"]),
        json=payload,
    )
    assert created.status_code == 200
    assert created.json()["role"] == "caretaker"
    assert created.json()["username"] == "new-caretaker"
    assert "password" not in created.json()
    created_user = db_session.query(User).filter_by(username="new-caretaker").one()
    assert created_user.password_hash != payload["password"]
    assert test_client.post(
        "/api/auth/token",
        data={"username": "new-caretaker", "password": payload["password"]},
    ).status_code == 200
    assert test_client.post(
        "/api/auth/users",
        headers=auth_headers(data["admin"]),
        json=payload,
    ).status_code == 409
    assert test_client.post(
        "/api/auth/users",
        headers=auth_headers(data["admin"]),
        json={**payload, "username": "multibyte-password", "password": "é" * 37},
    ).status_code == 422
    audit = db_session.query(AuditLog).filter_by(
        action="user_created",
        resource_id=str(created_user.id),
    ).one()
    assert audit.actor_id == data["admin"].id
    assert payload["password"] not in (audit.details or "")
    for role in UserRole:
        created_role = test_client.post(
            "/api/auth/users",
            headers=auth_headers(data["admin"]),
            json={
                "username": f"account-{role.value}",
                "password": "role-specific-secure-password",
                "role": role.value,
            },
        )
        assert created_role.status_code == 200
        assert created_role.json()["role"] == role.value


def test_doctor_assignments_control_prescription_creation(test_client, care_data, db_session):
    data = care_data
    valid_payload = {
        "resident_id": str(data["resident_record"].id),
        "medicine_id": str(data["medicine"].id),
        "dosage": "1 tablet",
        "frequency": "Daily",
        "scheduled_times": ["09:00"],
        "start_date": date.today().isoformat(),
    }
    for role in ("admin", "caretaker", "resident", "family"):
        response = test_client.post("/api/prescriptions", headers=auth_headers(data[role]), json=valid_payload)
        assert response.status_code == 403
    assert test_client.post(
        "/api/prescriptions",
        headers=auth_headers(data["doctor"]),
        json={**valid_payload, "resident_id": str(data["other_resident_record"].id)},
    ).status_code == 404
    unassigned_doctor = make_user(db_session, UserRole.DOCTOR, "unassigned-doctor")
    assert test_client.post(
        "/api/prescriptions",
        headers=auth_headers(unassigned_doctor),
        json=valid_payload,
    ).status_code == 404
    created = test_client.post("/api/prescriptions", headers=auth_headers(data["doctor"]), json=valid_payload)
    assert created.status_code == 201
    assert created.json()["doctor_id"] == str(data["doctor"].id)


def test_medicine_catalog_is_readable_but_only_admins_and_doctors_can_add(test_client, care_data):
    data = care_data
    medicine_payload = {"name": "Additional medicine", "strength": "10 mg"}
    for role in ("admin", "doctor", "other_doctor", "caretaker", "resident", "other_resident", "family"):
        headers = auth_headers(data[role])
        assert test_client.get("/api/medicines", headers=headers).status_code == 200
        response = test_client.post("/api/medicines", headers=headers, json=medicine_payload)
        if role in {"admin", "doctor", "other_doctor"}:
            assert response.status_code == 201
        else:
            assert response.status_code == 403


def test_only_prescribing_doctor_can_update_or_discontinue(test_client, care_data, db_session):
    data = care_data
    prescription_id = data["prescription"].id
    update = {"dosage": "2 tablets"}
    for role in ("admin", "caretaker", "resident", "family"):
        headers = auth_headers(data[role])
        assert test_client.put(f"/api/prescriptions/{prescription_id}", headers=headers, json=update).status_code == 403
        assert test_client.post(
            f"/api/prescriptions/{prescription_id}/discontinue",
            headers=headers,
            json={"reason": "review"},
        ).status_code == 403
    assert test_client.put(
        f"/api/prescriptions/{prescription_id}",
        headers=auth_headers(data["other_doctor"]),
        json=update,
    ).status_code == 404
    assert test_client.put(
        f"/api/prescriptions/{prescription_id}",
        headers=auth_headers(data["doctor"]),
        json={"status": "discontinued"},
    ).status_code == 422
    updated = test_client.put(
        f"/api/prescriptions/{prescription_id}",
        headers=auth_headers(data["doctor"]),
        json=update,
    )
    assert updated.status_code == 200
    assert updated.json()["dosage"] == "2 tablets"
    discontinued = test_client.post(
        f"/api/prescriptions/{prescription_id}/discontinue",
        headers=auth_headers(data["doctor"]),
        json={"reason": "No longer needed"},
    )
    assert discontinued.status_code == 200
    assert discontinued.json()["status"] == "discontinued"
    audit = db_session.query(PrescriptionHistory).filter_by(
        prescription_id=prescription_id,
        change_type="discontinued",
    ).one()
    assert json.loads(audit.after_state)["discontinuation_reason"] == "No longer needed"
    assert test_client.post(
        f"/api/prescriptions/{prescription_id}/discontinue",
        headers=auth_headers(data["doctor"]),
        json={"reason": "again"},
    ).status_code == 409


def test_caretaker_and_doctor_assignments_are_admin_managed(test_client, care_data):
    data = care_data
    resident_id = data["other_resident_record"].id
    admin_headers = auth_headers(data["admin"])
    for role in ("doctor", "caretaker", "resident", "family"):
        assert test_client.post(
            f"/api/residents/{resident_id}/assignments/caretakers",
            headers=auth_headers(data[role]),
            json={"user_id": str(data["caretaker"].id)},
        ).status_code == 403
    assigned = test_client.post(
        f"/api/residents/{resident_id}/assignments/caretakers",
        headers=admin_headers,
        json={"user_id": str(data["caretaker"].id)},
    )
    assert assigned.status_code == 201
    assert assigned.json()["is_active"] is True
    assert test_client.post(
        f"/api/residents/{resident_id}/assignments/caretakers",
        headers=admin_headers,
        json={"user_id": str(data["caretaker"].id)},
    ).status_code == 409
    wrong_role = test_client.post(
        f"/api/residents/{resident_id}/assignments/doctors",
        headers=admin_headers,
        json={"user_id": str(data["family"].id)},
    )
    assert wrong_role.status_code == 404
    assert test_client.get(f"/api/residents/{resident_id}", headers=auth_headers(data["caretaker"])).status_code == 200
    assert test_client.delete(
        f"/api/residents/{resident_id}/assignments/caretakers/{data['caretaker'].id}",
        headers=admin_headers,
    ).status_code == 204
    assert test_client.get(
        f"/api/residents/{resident_id}",
        headers=auth_headers(data["caretaker"]),
    ).status_code == 404


def test_family_must_request_then_receive_and_can_lose_resident_consent(test_client, care_data):
    data = care_data
    resident_id = data["other_resident_record"].id
    family_headers = auth_headers(data["family"])
    resident_headers = auth_headers(data["other_resident"])

    request = test_client.post(f"/api/family-links/{resident_id}", headers=family_headers)
    assert request.status_code == 201
    pending_link = test_client.get("/api/family-links", headers=family_headers)
    assert pending_link.status_code == 200
    requested_link = next(link for link in pending_link.json() if link["resident_id"] == str(resident_id))
    assert requested_link["resident_name"] is None
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 404
    pending = test_client.get(
        f"/api/residents/{resident_id}/family-consents",
        headers=resident_headers,
    )
    assert pending.status_code == 200
    assert pending.json()[0]["family_member_id"] == str(data["family"].id)

    approved = test_client.post(
        f"/api/residents/{resident_id}/family-consent",
        headers=resident_headers,
        json={
            "family_member_id": str(data["family"].id),
            "relationship_type": "child",
            "can_view_profile": True,
            "can_view_prescriptions": True,
        },
    )
    assert approved.status_code == 201
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 200
    linked_resident = next(
        link for link in test_client.get("/api/family-links", headers=family_headers).json()
        if link["resident_id"] == str(resident_id)
    )
    assert linked_resident["resident_name"] == "Resident Two"

    revoked = test_client.delete(
        f"/api/residents/{resident_id}/family-consent/{data['family'].id}",
        headers=resident_headers,
    )
    assert revoked.status_code == 204
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 404
    assert all(
        link["resident_id"] != str(resident_id)
        for link in test_client.get("/api/family-links", headers=family_headers).json()
    )
    assert test_client.post(f"/api/family-links/{resident_id}", headers=family_headers).status_code == 201
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 404
    assert test_client.post(
        f"/api/residents/{resident_id}/family-consent",
        headers=resident_headers,
        json={
            "family_member_id": str(data["family"].id),
            "can_view_profile": True,
            "can_view_prescriptions": True,
        },
    ).status_code == 201
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 200


def test_family_profile_and_prescription_permissions_are_independent(test_client, care_data):
    data = care_data
    resident_id = data["other_resident_record"].id
    family_headers = auth_headers(data["family"])
    resident_headers = auth_headers(data["other_resident"])

    assert test_client.post(f"/api/family-links/{resident_id}", headers=family_headers).status_code == 201
    approved = test_client.post(
        f"/api/residents/{resident_id}/family-consent",
        headers=resident_headers,
        json={
            "family_member_id": str(data["family"].id),
            "can_view_profile": False,
            "can_view_prescriptions": True,
        },
    )
    assert approved.status_code == 201
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 404
    prescriptions = test_client.get("/api/prescriptions", headers=family_headers)
    assert prescriptions.status_code == 200
    assert {item["id"] for item in prescriptions.json()} == {
        str(data["prescription"].id),
        str(data["other_prescription"].id),
    }
    family_links = test_client.get("/api/family-links", headers=family_headers).json()
    other_link = next(item for item in family_links if item["resident_id"] == str(resident_id))
    assert other_link["resident_name"] is None
    assert other_link["can_view_profile"] is False
    assert other_link["can_view_prescriptions"] is True

    updated = test_client.patch(
        f"/api/residents/{resident_id}/family-consent/{data['family'].id}",
        headers=resident_headers,
        json={"can_view_profile": True, "can_view_prescriptions": False},
    )
    assert updated.status_code == 200
    assert test_client.get(f"/api/residents/{resident_id}", headers=family_headers).status_code == 200
    prescriptions = test_client.get("/api/prescriptions", headers=family_headers)
    assert prescriptions.status_code == 200
    assert {item["id"] for item in prescriptions.json()} == {str(data["prescription"].id)}
    assert test_client.patch(
        f"/api/residents/{resident_id}/family-consent/{data['family'].id}",
        headers=resident_headers,
        json={"can_view_profile": False, "can_view_prescriptions": False},
    ).status_code == 422


def test_assignment_and_family_ids_cannot_be_used_to_escalate_access(test_client, care_data, db_session):
    data = care_data
    admin_headers = auth_headers(data["admin"])
    resident_id = data["other_resident_record"].id
    invalid_role = test_client.post(
        f"/api/residents/{resident_id}/assignments/caretakers",
        headers=admin_headers,
        json={"user_id": str(data["family"].id)},
    )
    assert invalid_role.status_code == 404

    other_family = make_user(db_session, UserRole.FAMILY_MEMBER, "other-family")
    assert test_client.get("/api/family-links", headers=auth_headers(other_family)).json() == []
    assert test_client.delete(
        f"/api/residents/{data['resident_record'].id}/family-consent/{data['family'].id}",
        headers=auth_headers(other_family),
    ).status_code == 404
    assert test_client.post(
        f"/api/residents/{data['resident_record'].id}/family-consent",
        headers=auth_headers(data["family"]),
        json={
            "family_member_id": str(data["other_doctor"].id),
            "can_view_profile": True,
            "can_view_prescriptions": False,
        },
    ).status_code == 403


def test_inactive_users_and_logout_revoke_tokens(test_client, db_session):
    inactive = make_user(db_session, UserRole.RESIDENT, "inactive-user", is_active=False)
    old_token = auth_headers(inactive)
    assert test_client.get("/api/auth/me", headers=old_token).status_code == 403
    login = test_client.post(
        "/api/auth/token",
        data={"username": inactive.username, "password": "test-password-123"},
    )
    assert login.status_code == 403

    active = make_user(db_session, UserRole.ADMIN, "logout-user")
    login = test_client.post(
        "/api/auth/token",
        data={"username": active.username, "password": "test-password-123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    token = {"Authorization": f"Bearer {login.json()['access_token']}"}
    other_session = auth_headers(active)
    assert test_client.get("/api/auth/me", headers=token).json()["username"] == active.username
    assert test_client.post("/api/auth/logout", headers=token).status_code == 204
    assert test_client.get("/api/auth/me", headers=token).status_code == 401
    assert test_client.get("/api/auth/me", headers=other_session).status_code == 401
    assert test_client.post(
        "/api/auth/token",
        data={"username": active.username, "password": "incorrect-password"},
    ).status_code == 401


def test_admin_account_deactivation_is_role_scoped_and_invalidates_tokens(test_client, care_data):
    data = care_data
    resident = data["other_resident"]
    resident_token = auth_headers(resident)
    admin_headers = auth_headers(data["admin"])
    self_deactivate = test_client.patch(
        f"/api/auth/users/{data['admin'].id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 409

    deactivated = test_client.patch(
        f"/api/auth/users/{resident.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert test_client.get("/api/auth/me", headers=resident_token).status_code == 401
    assert test_client.patch(
        f"/api/auth/users/{resident.id}",
        headers=admin_headers,
        json={"is_active": True, "role": "admin"},
    ).status_code == 422

    reactivated = test_client.patch(
        f"/api/auth/users/{resident.id}",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert reactivated.status_code == 200
    assert test_client.get("/api/auth/me", headers=resident_token).status_code == 401


def test_malformed_and_expired_bearer_tokens_are_rejected(test_client, care_data):
    user = care_data["admin"]
    assert test_client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    expired = create_access_token(
        {"sub": user.username, "ver": user.token_version},
        expires_delta=__import__("datetime").timedelta(seconds=-1),
    )
    assert test_client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_production_settings_reject_known_or_short_jwt_secret():
    from pydantic import ValidationError
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="dev-insecure-change-me")
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="too-short")
    secret = secrets.token_urlsafe(48)
    assert Settings(ENVIRONMENT="production", SECRET_KEY=secret).SECRET_KEY == secret
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="a" * 48)


def test_database_urls_use_the_installed_postgresql_driver():
    from app.db.base import normalize_database_url

    assert normalize_database_url("postgres://db.example/care") == "postgresql+psycopg2://db.example/care"
    assert normalize_database_url("postgresql://db.example/care") == "postgresql+psycopg2://db.example/care"
    configured = "postgresql+psycopg://db.example/care"
    assert normalize_database_url(configured) == configured

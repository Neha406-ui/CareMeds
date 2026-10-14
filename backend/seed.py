"""
CareMeds — Database Seed Script
================================
Populates the database with realistic dummy data for every role:
  • 1 Admin (already created, skipped if present)
  • 2 Doctors
  • 3 Caretakers
  • 5 Residents (with linked resident-role users)
  • 3 Family Members

Then seeds:
  • 10 Medicines
  • 12 Prescriptions (active, discontinued, on_hold)
  • Caretaker assignments (each caretaker → 2 residents)
  • Family links with consent granted

Run from:  cd backend && python seed.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/caremeds")
# Render uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
Session = sessionmaker(bind=engine)

from app.models.user import User, UserRole
from app.models.resident import Resident
from app.models.prescription import Medicine, Prescription, PrescriptionStatus
from app.models.assignment import CaretakerAssignment
from app.models.family import FamilyLink
from app.core.security import get_password_hash


# ─── helpers ────────────────────────────────────────────────────────────────

def get_or_create_user(db, username, password, role, full_name, phone=None):
    u = db.query(User).filter(User.username == username).first()
    if u:
        print(f"  [skip] user '{username}' already exists")
        return u
    u = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
        full_name=full_name,
        phone=phone,
        is_active=True,
    )
    db.add(u)
    db.flush()
    print(f"  [+] user '{username}'  ({role.value})")
    return u


def get_or_create_medicine(db, name, strength, form, manufacturer, reorder_level=10):
    m = db.query(Medicine).filter(Medicine.name == name).first()
    if m:
        print(f"  [skip] medicine '{name}' already exists")
        return m
    m = Medicine(
        name=name,
        strength=strength,
        form=form,
        manufacturer=manufacturer,
        reorder_level=reorder_level,
        is_active=True,
    )
    db.add(m)
    db.flush()
    print(f"  [+] medicine '{name}'")
    return m


# ─── main ────────────────────────────────────────────────────────────────────

db = Session()

try:
    print("\n═══ USERS ═══")

    # Admin (may already exist)
    admin = get_or_create_user(db, "admin", "Admin@CareMeds2026",
                               UserRole.ADMIN, "System Administrator", "+91-9000000001")

    # Doctors
    dr_sara   = get_or_create_user(db, "dr.sara",   "Doctor@Sara2026!",
                                    UserRole.DOCTOR, "Dr. Sara Mathew", "+91-9000000002")
    dr_rahul  = get_or_create_user(db, "dr.rahul",  "Doctor@Rahul2026!",
                                    UserRole.DOCTOR, "Dr. Rahul Nair", "+91-9000000003")

    # Caretakers
    care_anita  = get_or_create_user(db, "anita.care",  "Caretaker@Anita26!",
                                      UserRole.CARETAKER, "Anita Sharma", "+91-9000000004")
    care_joseph = get_or_create_user(db, "joseph.care", "Caretaker@Joseph26!",
                                      UserRole.CARETAKER, "Joseph Thomas", "+91-9000000005")
    care_priya  = get_or_create_user(db, "priya.care",  "Caretaker@Priya26!",
                                      UserRole.CARETAKER, "Priya Menon", "+91-9000000006")

    # Resident users (linked to resident profiles below)
    res_user1 = get_or_create_user(db, "ramesh.r",  "Resident@Ram26!",
                                    UserRole.RESIDENT, "Ramesh Rao", "+91-9000000007")
    res_user2 = get_or_create_user(db, "meena.v",   "Resident@Mee26!",
                                    UserRole.RESIDENT, "Meena Venkat", "+91-9000000008")
    res_user3 = get_or_create_user(db, "george.k",  "Resident@Geo26!",
                                    UserRole.RESIDENT, "George Kurian", "+91-9000000009")
    res_user4 = get_or_create_user(db, "fatima.s",  "Resident@Fat26!",
                                    UserRole.RESIDENT, "Fatima Sheikh", "+91-9000000010")
    res_user5 = get_or_create_user(db, "lakshmi.p", "Resident@Lak26!",
                                    UserRole.RESIDENT, "Lakshmi Pillai", "+91-9000000011")

    # Family members
    fam_arjun  = get_or_create_user(db, "arjun.fam",  "Family@Arj26!",
                                     UserRole.FAMILY_MEMBER, "Arjun Rao", "+91-9000000012")
    fam_sunita = get_or_create_user(db, "sunita.fam", "Family@Sun26!",
                                     UserRole.FAMILY_MEMBER, "Sunita Kurian", "+91-9000000013")
    fam_omar   = get_or_create_user(db, "omar.fam",   "Family@Omar26!",
                                     UserRole.FAMILY_MEMBER, "Omar Sheikh", "+91-9000000014")

    db.commit()

    # ─── RESIDENTS ──────────────────────────────────────────────────────────
    print("\n═══ RESIDENTS ═══")

    def get_or_create_resident(db, user, full_name, dob_str, room, emergency, allergies, care_notes):
        existing = db.query(Resident).filter(Resident.user_id == user.id).first()
        if existing:
            print(f"  [skip] resident profile for '{user.username}' already exists")
            return existing
        r = Resident(
            user_id=user.id,
            full_name=full_name,
            dob=date.fromisoformat(dob_str),
            room_number=room,
            emergency_contact=emergency,
            allergies=allergies,
            care_notes=care_notes,
            is_active=True,
        )
        db.add(r)
        db.flush()
        print(f"  [+] resident '{full_name}' in room {room}")
        return r

    res1 = get_or_create_resident(db, res_user1,
        "Ramesh Rao",        "1948-03-15", "A-101",
        "Arjun Rao (Son) — +91-9000000012",
        "Penicillin, Sulfa drugs",
        "Requires low-sodium diet. Diabetic. Morning physiotherapy Mon/Wed/Fri.")

    res2 = get_or_create_resident(db, res_user2,
        "Meena Venkat",      "1952-07-22", "A-102",
        "Kavitha Venkat (Daughter) — +91-9100000001",
        "None known",
        "Hypertensive. Prefers vegetarian meals. Hearing aid — right ear.")

    res3 = get_or_create_resident(db, res_user3,
        "George Kurian",     "1945-11-04", "B-201",
        "Sunita Kurian (Daughter) — +91-9000000013",
        "Aspirin (rash), Shellfish",
        "Post-CABG care. Cardiac diet strictly followed. Weekly ECG monitoring.")

    res4 = get_or_create_resident(db, res_user4,
        "Fatima Sheikh",     "1955-05-30", "B-202",
        "Omar Sheikh (Son) — +91-9000000014",
        "Latex gloves trigger skin reaction",
        "Insulin-dependent diabetic. Foot examination daily. Prayer time 5 ×/day.")

    res5 = get_or_create_resident(db, res_user5,
        "Lakshmi Pillai",    "1950-09-18", "C-301",
        "Rajan Pillai (Husband) — +91-9200000001",
        "None known",
        "Mild dementia. Reality-orientation board in room. Escorted for all outdoor activities.")

    db.commit()

    # ─── MEDICINES ──────────────────────────────────────────────────────────
    print("\n═══ MEDICINES ═══")

    med_metformin  = get_or_create_medicine(db, "Metformin",       "500 mg",   "Tablet",  "Sun Pharma",    50)
    med_glipizide  = get_or_create_medicine(db, "Glipizide",       "5 mg",     "Tablet",  "Cipla",         30)
    med_amlodipine = get_or_create_medicine(db, "Amlodipine",      "5 mg",     "Tablet",  "Lupin",         40)
    med_atenolol   = get_or_create_medicine(db, "Atenolol",        "50 mg",    "Tablet",  "Alkem",         40)
    med_aspirin    = get_or_create_medicine(db, "Aspirin",         "75 mg",    "Tablet",  "Bayer",         60)
    med_atorvast   = get_or_create_medicine(db, "Atorvastatin",    "20 mg",    "Tablet",  "Torrent",       35)
    med_omeprazole = get_or_create_medicine(db, "Omeprazole",      "20 mg",    "Capsule", "Abbott",        45)
    med_insulin    = get_or_create_medicine(db, "Insulin Glargine","100 IU/mL","Injection","Novo Nordisk",  20)
    med_donepezil  = get_or_create_medicine(db, "Donepezil",       "5 mg",     "Tablet",  "Dr. Reddy's",   15)
    med_losartan   = get_or_create_medicine(db, "Losartan",        "50 mg",    "Tablet",  "Glenmark",      40)

    db.commit()

    # ─── PRESCRIPTIONS ──────────────────────────────────────────────────────
    print("\n═══ PRESCRIPTIONS ═══")

    today = date.today()

    def make_rx(db, resident, doctor, medicine, dosage, route, frequency,
                scheduled_times, instructions, start_offset, end_offset=None,
                status=PrescriptionStatus.ACTIVE):
        existing = db.query(Prescription).filter(
            Prescription.resident_id == resident.id,
            Prescription.medicine_id == medicine.id,
            Prescription.status == status,
        ).first()
        if existing:
            print(f"  [skip] prescription {medicine.name} → {resident.full_name}")
            return existing
        rx = Prescription(
            resident_id=resident.id,
            doctor_id=doctor.id,
            medicine_id=medicine.id,
            dosage=dosage,
            route=route,
            frequency=frequency,
            scheduled_times=scheduled_times,
            timezone="Asia/Kolkata",
            instructions=instructions,
            start_date=today + timedelta(days=start_offset),
            end_date=(today + timedelta(days=end_offset)) if end_offset else None,
            status=status,
            prescribed_at=datetime.utcnow() + timedelta(days=start_offset),
        )
        db.add(rx)
        db.flush()
        print(f"  [+] Rx {medicine.name} ({status.value}) → {resident.full_name}")
        return rx

    # Ramesh Rao — diabetic
    make_rx(db, res1, dr_sara, med_metformin,  "500 mg",  "Oral", "Twice daily",
            ["08:00","20:00"], "Take with meals. Monitor blood sugar before each dose.", -30)
    make_rx(db, res1, dr_sara, med_glipizide,  "5 mg",    "Oral", "Once daily",
            ["07:30"], "Take 30 minutes before breakfast.", -30)
    make_rx(db, res1, dr_rahul, med_atenolol,  "50 mg",   "Oral", "Once daily",
            ["08:00"], "Monitor heart rate. Hold if HR < 50 bpm.", -20)

    # Meena Venkat — hypertensive
    make_rx(db, res2, dr_rahul, med_amlodipine,"5 mg",    "Oral", "Once daily",
            ["09:00"], "Take at the same time each day. Check BP twice daily.", -45)
    make_rx(db, res2, dr_rahul, med_losartan,  "50 mg",   "Oral", "Once daily",
            ["09:00"], "Monitor potassium levels monthly.", -45)
    make_rx(db, res2, dr_sara,  med_omeprazole,"20 mg",   "Oral", "Once daily",
            ["07:00"], "Take 30 minutes before first meal.", -45,
            status=PrescriptionStatus.DISCONTINUED)

    # George Kurian — post-cardiac
    make_rx(db, res3, dr_rahul, med_aspirin,   "75 mg",   "Oral", "Once daily",
            ["08:00"], "Do NOT crush tablet. Take with food.", -60)
    make_rx(db, res3, dr_rahul, med_atorvast,  "20 mg",   "Oral", "Once daily at night",
            ["21:00"], "Grapefruit juice contraindicated.", -60)

    # Fatima Sheikh — insulin-dependent diabetic
    make_rx(db, res4, dr_sara,  med_insulin,   "20 IU",   "Subcutaneous","Once daily at bedtime",
            ["22:00"], "Rotate injection sites. Store insulin in refrigerator.", -15)
    make_rx(db, res4, dr_sara,  med_metformin, "500 mg",  "Oral", "Twice daily",
            ["08:00","20:00"], "Take with meals.", -15,
            status=PrescriptionStatus.ON_HOLD)

    # Lakshmi Pillai — dementia
    make_rx(db, res5, dr_sara,  med_donepezil, "5 mg",    "Oral", "Once daily at bedtime",
            ["21:30"], "Administer with caretaker supervision. Watch for nausea.", -90)
    make_rx(db, res5, dr_rahul, med_omeprazole,"20 mg",   "Oral", "Once daily",
            ["07:00"], "Take on empty stomach.", -90)

    db.commit()

    # ─── CARETAKER ASSIGNMENTS ──────────────────────────────────────────────
    print("\n═══ CARETAKER ASSIGNMENTS ═══")

    def assign(db, caretaker, resident, assigner):
        existing = db.query(CaretakerAssignment).filter(
            CaretakerAssignment.caretaker_id == caretaker.id,
            CaretakerAssignment.resident_id  == resident.id,
            CaretakerAssignment.is_active    == True,
        ).first()
        if existing:
            print(f"  [skip] {caretaker.full_name} → {resident.full_name}")
            return existing
        a = CaretakerAssignment(
            caretaker_id=caretaker.id,
            resident_id=resident.id,
            assigned_by=assigner.id,
            is_active=True,
        )
        db.add(a)
        db.flush()
        print(f"  [+] {caretaker.full_name} assigned to {resident.full_name}")
        return a

    assign(db, care_anita,  res1, admin)   # Anita → Ramesh
    assign(db, care_anita,  res2, admin)   # Anita → Meena
    assign(db, care_joseph, res3, admin)   # Joseph → George
    assign(db, care_joseph, res4, admin)   # Joseph → Fatima
    assign(db, care_priya,  res5, admin)   # Priya → Lakshmi
    assign(db, care_priya,  res1, admin)   # Priya → Ramesh (shared care)

    db.commit()

    # ─── FAMILY LINKS ───────────────────────────────────────────────────────
    print("\n═══ FAMILY LINKS ═══")

    def link_family(db, resident, family_member, relationship_type,
                    can_view_profile, can_view_rx, consent_granted_by):
        existing = db.query(FamilyLink).filter(
            FamilyLink.resident_id      == resident.id,
            FamilyLink.family_member_id == family_member.id,
            FamilyLink.is_active        == True,
        ).first()
        if existing:
            print(f"  [skip] {family_member.full_name} → {resident.full_name}")
            return existing
        fl = FamilyLink(
            resident_id=resident.id,
            family_member_id=family_member.id,
            relationship_type=relationship_type,
            consent_granted=True,
            can_view_profile=can_view_profile,
            can_view_prescriptions=can_view_rx,
            consent_granted_at=datetime.utcnow(),
            consent_granted_by=consent_granted_by.id,
            is_active=True,
        )
        db.add(fl)
        db.flush()
        print(f"  [+] {family_member.full_name} ({relationship_type}) linked to {resident.full_name}")
        return fl

    # Arjun Rao is son of Ramesh Rao (res1)
    link_family(db, res1, fam_arjun, "Son",
                can_view_profile=True, can_view_rx=True,
                consent_granted_by=res_user1)

    # Sunita Kurian is daughter of George Kurian (res3)
    link_family(db, res3, fam_sunita, "Daughter",
                can_view_profile=True, can_view_rx=True,
                consent_granted_by=res_user3)

    # Omar Sheikh is son of Fatima Sheikh (res4)
    link_family(db, res4, fam_omar,   "Son",
                can_view_profile=True, can_view_rx=False,
                consent_granted_by=res_user4)

    db.commit()

    # ─── SUMMARY ────────────────────────────────────────────────────────────
    print("\n" + "═"*55)
    print("  SEED COMPLETE — Login Credentials")
    print("═"*55)
    creds = [
        ("Admin",           "admin",       "Admin@CareMeds2026"),
        ("Doctor",          "dr.sara",     "Doctor@Sara2026!"),
        ("Doctor",          "dr.rahul",    "Doctor@Rahul2026!"),
        ("Caretaker",       "anita.care",  "Caretaker@Anita26!"),
        ("Caretaker",       "joseph.care", "Caretaker@Joseph26!"),
        ("Caretaker",       "priya.care",  "Caretaker@Priya26!"),
        ("Resident",        "ramesh.r",    "Resident@Ram26!"),
        ("Resident",        "meena.v",     "Resident@Mee26!"),
        ("Resident",        "george.k",    "Resident@Geo26!"),
        ("Resident",        "fatima.s",    "Resident@Fat26!"),
        ("Resident",        "lakshmi.p",   "Resident@Lak26!"),
        ("Family Member",   "arjun.fam",   "Family@Arj26!"),
        ("Family Member",   "sunita.fam",  "Family@Sun26!"),
        ("Family Member",   "omar.fam",    "Family@Omar26!"),
    ]
    print(f"  {'Role':<16} {'Username':<14} {'Password'}")
    print(f"  {'-'*16} {'-'*14} {'-'*22}")
    for role, uname, pwd in creds:
        print(f"  {role:<16} {uname:<14} {pwd}")
    print("═"*55 + "\n")

finally:
    db.close()
    engine.dispose()

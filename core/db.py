"""Database layer (SQLAlchemy). SQLite by default, Postgres when DATABASE_URL is set."""
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, MetaData,
    String, Table, Text, create_engine, func, insert, select, update,
)

from core import alerts as alert_rules
from core.config import get_secret

metadata = MetaData()

patients_t = Table(
    "patients", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(120), nullable=False),
    Column("age", Integer), Column("sex", String(1)), Column("chest_pain", String(3)),
    Column("resting_bp", Float), Column("cholesterol", Float), Column("fasting_bs", Integer),
    Column("resting_ecg", String(10)), Column("max_hr", Float), Column("exercise_angina", String(1)),
    Column("oldpeak", Float), Column("st_slope", String(10)),
    Column("created_at", DateTime, default=datetime.utcnow),
)
vitals_t = Table(
    "vitals", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), index=True),
    Column("recorded_on", Date), Column("systolic_bp", Float),
    Column("heart_rate", Float), Column("cholesterol", Float),
)
alerts_t = Table(
    "alerts", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), index=True),
    Column("alert_date", Date), Column("metric", String(30)), Column("reason", Text),
    Column("severity", String(10)), Column("reviewed", Boolean, default=False),
)
reports_t = Table(
    "reports", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), index=True),
    Column("filename", String(255)), Column("uploaded_at", DateTime, default=datetime.utcnow),
    Column("content", LargeBinary),
)
history_t = Table(
    "history", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), index=True),
    Column("event_date", Date), Column("note", Text),
)


@st.cache_resource
def get_engine():
    url = get_secret("DATABASE_URL", "sqlite:///cardioiq.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url, pool_pre_ping=True)
    metadata.create_all(engine)
    with engine.connect() as conn:
        count = conn.execute(select(func.count()).select_from(patients_t)).scalar()
    if count == 0:
        from core.seed import seed  # imported lazily to avoid a circular import
        seed(engine)
    return engine


def _read(query) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


# ---------- patients ----------
def get_patients() -> pd.DataFrame:
    return _read(select(patients_t))


def get_patient(pid: int) -> dict | None:
    df = _read(select(patients_t).where(patients_t.c.id == pid))
    return None if df.empty else df.iloc[0].to_dict()


def add_patient(data: dict, initial_hr: float) -> int:
    today = date.today()
    with get_engine().begin() as conn:
        pid = conn.execute(insert(patients_t).values(**data)).inserted_primary_key[0]
        conn.execute(insert(vitals_t).values(
            patient_id=pid, recorded_on=today, systolic_bp=data["resting_bp"],
            heart_rate=initial_hr, cholesterol=data["cholesterol"]))
        conn.execute(insert(history_t).values(
            patient_id=pid, event_date=today, note="Patient registered; baseline vitals recorded."))
    return int(pid)


# ---------- vitals ----------
def get_vitals(pid: int | None = None) -> pd.DataFrame:
    q = select(vitals_t)
    if pid is not None:
        q = q.where(vitals_t.c.patient_id == pid)
    df = _read(q)
    df["recorded_on"] = pd.to_datetime(df["recorded_on"])
    return df.sort_values(["patient_id", "recorded_on"]).reset_index(drop=True)


def add_vitals(pid: int, recorded_on: date, sbp: float, hr: float, chol: float) -> list[dict]:
    """Store a reading, run the alert rules on it, store and return any alerts."""
    prev = get_vitals(pid)
    row = {"systolic_bp": sbp, "heart_rate": hr, "cholesterol": chol}
    found = alert_rules.evaluate_reading(prev, row)
    with get_engine().begin() as conn:
        conn.execute(insert(vitals_t).values(
            patient_id=pid, recorded_on=recorded_on, systolic_bp=sbp, heart_rate=hr, cholesterol=chol))
        for a in found:
            conn.execute(insert(alerts_t).values(
                patient_id=pid, alert_date=recorded_on, reviewed=False, **a))
    return found


# ---------- alerts ----------
def get_alerts(pid: int | None = None, only_open: bool = False) -> pd.DataFrame:
    q = select(alerts_t, patients_t.c.name.label("patient_name")).join(
        patients_t, patients_t.c.id == alerts_t.c.patient_id)
    if pid is not None:
        q = q.where(alerts_t.c.patient_id == pid)
    if only_open:
        q = q.where(alerts_t.c.reviewed == False)  # noqa: E712
    df = _read(q)
    df["alert_date"] = pd.to_datetime(df["alert_date"])
    return df.sort_values("alert_date", ascending=False).reset_index(drop=True)


def mark_reviewed(alert_id: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(update(alerts_t).where(alerts_t.c.id == alert_id).values(reviewed=True))


# ---------- reports ----------
def add_report(pid: int, filename: str, content: bytes) -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(reports_t).values(patient_id=pid, filename=filename, content=content))
        conn.execute(insert(history_t).values(
            patient_id=pid, event_date=date.today(), note=f"Report uploaded: {filename}"))


def list_reports(pid: int) -> pd.DataFrame:
    q = select(reports_t.c.id, reports_t.c.filename, reports_t.c.uploaded_at).where(
        reports_t.c.patient_id == pid).order_by(reports_t.c.uploaded_at.desc())
    return _read(q)


def get_report_content(report_id: int) -> bytes:
    with get_engine().connect() as conn:
        return conn.execute(select(reports_t.c.content).where(reports_t.c.id == report_id)).scalar()


# ---------- history ----------
def add_history(pid: int, note: str, event_date: date | None = None) -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(history_t).values(
            patient_id=pid, event_date=event_date or date.today(), note=note))


def get_history(pid: int) -> pd.DataFrame:
    df = _read(select(history_t).where(history_t.c.patient_id == pid))
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df.sort_values(["event_date", "id"], ascending=False).reset_index(drop=True)



def migrate_local_changes_to_cloud():
    """One-time migration of verified local gender corrections and two patients."""

    gender_updates = {
        7: ("Deepa Krishnan", "F"),
        10: ("Anjali Sharma", "F"),
        11: ("Priya Nair", "F"),
        13: ("Lakshmi Reddy", "F"),
        14: ("Revathi Krishnan", "F"),
        15: ("Divya Patel", "F"),
        16: ("Suresh Iyer", "M"),
        19: ("Meera Das", "F"),
        20: ("Lakshmi Patel", "F"),
        25: ("Sunita Shetty", "F"),
        28: ("Meera Pillai", "F"),
        29: ("Kavya Gowda", "F"),
        30: ("Priya Sharma", "F"),
        31: ("Ananya Pillai", "F"),
        33: ("Revathi Sharma", "F"),
        34: ("Ramesh Rao", "M"),
        40: ("Meera Pillai", "F"),
        42: ("Aarav Pillai", "M"),
        44: ("Lakshmi Iyer", "F"),
        47: ("Priya Shetty", "F"),
        49: ("Manoj Krishnan", "M"),
        50: ("Arjun Gowda", "M"),
        51: ("Karthik Patel", "M"),
        52: ("Meera Nair", "F"),
        53: ("Karthik Rao", "M"),
        54: ("Priya Shetty", "F"),
        56: ("Kavya Patel", "F"),
    }

    new_patients = [
        {
            "id": 61, "name": "Vikram Reddy", "age": 67, "sex": "M",
            "chest_pain": "ASY", "resting_bp": 165.0,
            "cholesterol": 290.0, "fasting_bs": 1,
            "resting_ecg": "ST", "max_hr": 105.0,
            "exercise_angina": "Y", "oldpeak": 2.5,
            "st_slope": "Down",
            "created_at": datetime.fromisoformat("2026-11-24 16:45:20.509805"),
        },
        {
            "id": 62, "name": "Goutham Karthik", "age": 28, "sex": "M",
            "chest_pain": "ASY", "resting_bp": 110.0,
            "cholesterol": 165.0, "fasting_bs": 0,
            "resting_ecg": "Normal", "max_hr": 190.0,
            "exercise_angina": "N", "oldpeak": 0.0,
            "st_slope": "Up",
            "created_at": datetime.fromisoformat("2026-11-24 16:47:02.304831"),
        },
    ]

    new_vitals = [
        {
            "patient_id": 61, "recorded_on": date(2026, 11, 24),
            "systolic_bp": 165.0, "heart_rate": 95.0,
            "cholesterol": 290.0,
        },
        {
            "patient_id": 62, "recorded_on": date(2026, 11, 24),
            "systolic_bp": 110.0, "heart_rate": 68.0,
            "cholesterol": 165.0,
        },
    ]

    new_history = [
        {
            "patient_id": 61, "event_date": date(2026, 11, 24),
            "note": "Patient registered; baseline vitals recorded.",
        },
        {
            "patient_id": 62, "event_date": date(2026, 11, 24),
            "note": "Patient registered; baseline vitals recorded.",
        },
    ]

    engine = get_engine()

    with engine.begin() as conn:

        # Verify existing patient IDs and names
        for pid, (expected_name, gender) in gender_updates.items():
            patient = conn.execute(
                select(patients_t.c.name).where(patients_t.c.id == pid)
            ).scalar_one_or_none()

            if patient != expected_name:
                raise ValueError(
                    f"Verification failed for patient ID {pid}. "
                    "No migration was applied."
                )

        # Ensure new patient IDs do not already exist
        for patient in new_patients:
            existing = conn.execute(
                select(patients_t.c.id).where(
                    patients_t.c.id == patient["id"]
                )
            ).first()

            if existing:
                raise ValueError(
                    f"Patient ID {patient['id']} already exists. "
                    "Migration stopped to prevent duplicates."
                )

        # Update gender only
        for pid, (_, gender) in gender_updates.items():
            conn.execute(
                update(patients_t)
                .where(patients_t.c.id == pid)
                .values(sex=gender)
            )

        # Insert new patients with their original IDs
        for patient in new_patients:
            conn.execute(insert(patients_t).values(**patient))

        # Insert their associated vitals
        conn.execute(insert(vitals_t), new_vitals)

        # Insert their registration history
        conn.execute(insert(history_t), new_history)

    return {
        "updated_genders": len(gender_updates),
        "new_patients": len(new_patients),
        "new_vitals": len(new_vitals),
        "new_history": len(new_history),
    }

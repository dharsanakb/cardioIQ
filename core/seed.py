"""Seed the database with patients from the Kaggle dataset plus SIMULATED vitals history.

Kaggle heart-disease data is one row per person (a snapshot). Each row becomes a patient's
baseline; 12 monthly readings are simulated around it, and ~35% of patients get a recent
deterioration so the alert engine has something to catch.
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import insert

from core import alerts as rules
from core.db import alerts_t, history_t, patients_t, vitals_t

FIRST = ["Aarav", "Ananya", "Karthik", "Meera", "Rohan", "Priya", "Suresh", "Lakshmi", "Vikram", "Divya",
         "Arjun", "Kavya", "Ramesh", "Sunita", "Naveen", "Anjali", "Harish", "Deepa", "Manoj", "Revathi"]
LAST = ["Iyer", "Nair", "Reddy", "Sharma", "Krishnan", "Gowda", "Menon", "Pillai", "Rao", "Patel", "Das", "Shetty"]


def seed(engine, n: int = 60, rng_seed: int = 7) -> None:
    path = Path(__file__).resolve().parent.parent / "data" / "heart.csv"
    if not path.exists():
        raise FileNotFoundError("data/heart.csv not found. Download it from Kaggle (see README).")

    raw = pd.read_csv(path)
    raw["Cholesterol"] = raw["Cholesterol"].replace(0, np.nan)
    raw["RestingBP"] = raw["RestingBP"].replace(0, np.nan)
    med_chol, med_bp = raw["Cholesterol"].median(), raw["RestingBP"].median()
    sample = raw.sample(n=min(n, len(raw)), random_state=rng_seed).reset_index(drop=True)

    rng = np.random.default_rng(rng_seed)
    today = date.today()
    n_read = 12
    dates = [today - timedelta(days=30 * (n_read - 1 - k)) for k in range(n_read)]

    with engine.begin() as conn:
        for _, r in sample.iterrows():
            bp0 = float(r["RestingBP"]) if pd.notna(r["RestingBP"]) else float(med_bp)
            chol0 = float(r["Cholesterol"]) if pd.notna(r["Cholesterol"]) else float(med_chol)
            pid = conn.execute(insert(patients_t).values(
                name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", age=int(r["Age"]), sex=r["Sex"],
                chest_pain=r["ChestPainType"], resting_bp=bp0, cholesterol=chol0,
                fasting_bs=int(r["FastingBS"]), resting_ecg=r["RestingECG"], max_hr=float(r["MaxHR"]),
                exercise_angina=r["ExerciseAngina"], oldpeak=float(r["Oldpeak"]), st_slope=r["ST_Slope"],
            )).inserted_primary_key[0]

            # simulated vitals history around the baseline
            sbp = bp0 + rng.normal(0, 4, n_read)
            hr = rng.integers(62, 86) + rng.normal(0, 4, n_read)
            chol = chol0 + rng.normal(0, 6, n_read)
            if rng.random() < 0.35:  # recent deterioration
                ramp = np.zeros(n_read)
                ramp[-int(rng.integers(1, 3)):] = 1
                sbp += ramp * rng.uniform(15, 30)
                hr += ramp * rng.uniform(12, 25)
                chol += ramp * chol0 * rng.uniform(0.08, 0.2)
            vit = pd.DataFrame({
                "recorded_on": dates,
                "systolic_bp": np.clip(sbp, 90, 210).round(0),
                "heart_rate": np.clip(hr, 45, 140).round(0),
                "cholesterol": np.clip(chol, 100, 500).round(0),
            })
            conn.execute(insert(vitals_t), [{"patient_id": pid, **row} for row in vit.to_dict("records")])

            for a in rules.evaluate_series(vit, last_n=4):
                conn.execute(insert(alerts_t).values(
                    patient_id=pid, reviewed=a["alert_date"] < today - timedelta(days=45), **a))

            conn.execute(insert(history_t), [
                {"patient_id": pid, "event_date": dates[0], "note": "Patient registered; baseline vitals recorded."},
                {"patient_id": pid, "event_date": dates[5], "note": "Routine cardiac check-up (simulated entry)."},
            ])

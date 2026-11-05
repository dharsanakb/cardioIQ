"""Glue between the database and the model: overview table and per-patient risk."""
import numpy as np
import pandas as pd

from core import db, model


def _apply_latest(patients: pd.DataFrame, bp, chol) -> pd.DataFrame:
    """Score patients using their most recent BP and cholesterol readings."""
    frame = patients.copy()
    frame["resting_bp"] = pd.Series(bp, index=frame.index).fillna(frame["resting_bp"])
    frame["cholesterol"] = pd.Series(chol, index=frame.index).fillna(frame["cholesterol"])
    return frame


def overview_table() -> pd.DataFrame:
    pts, vit, al = db.get_patients(), db.get_vitals(), db.get_alerts(only_open=True)
    last = vit.sort_values("recorded_on").groupby("patient_id").tail(1).drop(columns="id").rename(columns={
        "patient_id": "id", "recorded_on": "last_reading", "systolic_bp": "latest_bp",
        "heart_rate": "latest_hr", "cholesterol": "latest_chol"})
    last = last[["id", "last_reading", "latest_bp", "latest_hr", "latest_chol"]]
    df = pts.merge(last, on="id", how="left")

    scored = _apply_latest(df, df["latest_bp"], df["latest_chol"])
    df["risk_score"] = model.predict(scored)
    df["risk_level"] = [model.categorize(p) for p in df["risk_score"]]

    if al.empty:
        df["open_alerts"], df["high_alerts"] = 0, 0
    else:
        counts = al.groupby("patient_id").agg(
            open_alerts=("id", "count"), high_alerts=("severity", lambda s: int((s == "High").sum())))
        df = df.merge(counts, left_on="id", right_index=True, how="left")
        df[["open_alerts", "high_alerts"]] = df[["open_alerts", "high_alerts"]].fillna(0).astype(int)
    df["status"] = np.where(df["high_alerts"] > 0, "Needs review",
                            np.where(df["open_alerts"] > 0, "Monitoring", "Stable"))
    return df


def patient_risk(pid: int) -> dict:
    patient = db.get_patient(pid)
    vit = db.get_vitals(pid)
    row = pd.DataFrame([patient])
    if not vit.empty:
        row = _apply_latest(row, [vit.iloc[-1]["systolic_bp"]], [vit.iloc[-1]["cholesterol"]])
    score = float(model.predict(row)[0])
    return {
        "patient": {**patient, "resting_bp": row.iloc[0]["resting_bp"], "cholesterol": row.iloc[0]["cholesterol"]},
        "vitals": vit,
        "score": score,
        "category": model.categorize(score),
        "factors": model.explain(row),
    }

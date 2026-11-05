"""Rule-based alert engine.

Thresholds are ILLUSTRATIVE for a student prototype, not clinical guidelines.
Rules are used instead of ML on purpose: every alert is fully explainable.
"""
import pandas as pd

SEV_RANK = {"Low": 1, "Medium": 2, "High": 3}


def evaluate_reading(prev: pd.DataFrame, row) -> list[dict]:
    """Check one new reading against absolute limits and the patient's own baseline."""
    sbp = float(row["systolic_bp"])
    hr = float(row["heart_rate"])
    chol = float(row["cholesterol"])
    found = {"Blood pressure": [], "Heart rate": [], "Cholesterol": []}

    # --- absolute thresholds ---
    if sbp >= 160:
        found["Blood pressure"].append(("High", f"Systolic BP {sbp:.0f} mmHg is markedly elevated"))
    elif sbp >= 140:
        found["Blood pressure"].append(("Medium", f"Systolic BP {sbp:.0f} mmHg is elevated"))

    if hr > 120 or hr < 40:
        found["Heart rate"].append(("High", f"Resting heart rate {hr:.0f} bpm is far outside the normal range"))
    elif hr > 100 or hr < 50:
        found["Heart rate"].append(("Medium", f"Resting heart rate {hr:.0f} bpm is outside the normal range"))

    if chol >= 280:
        found["Cholesterol"].append(("High", f"Cholesterol {chol:.0f} mg/dL is very high"))
    elif chol >= 240:
        found["Cholesterol"].append(("Medium", f"Cholesterol {chol:.0f} mg/dL is high"))

    # --- change from the patient's own baseline (mean of up to 5 previous readings) ---
    if len(prev) >= 3:
        base = prev.tail(5)
        d_sbp = sbp - base["systolic_bp"].mean()
        d_hr = hr - base["heart_rate"].mean()
        pct_chol = (chol / base["cholesterol"].mean() - 1) * 100

        if d_sbp >= 20:
            found["Blood pressure"].append(("High", f"Systolic BP up {d_sbp:.0f} mmHg vs recent baseline"))
        elif d_sbp >= 12:
            found["Blood pressure"].append(("Medium", f"Systolic BP up {d_sbp:.0f} mmHg vs recent baseline"))

        if abs(d_hr) >= 20:
            found["Heart rate"].append(("High", f"Heart rate changed {d_hr:+.0f} bpm vs recent baseline"))
        elif abs(d_hr) >= 12:
            found["Heart rate"].append(("Medium", f"Heart rate changed {d_hr:+.0f} bpm vs recent baseline"))

        if pct_chol >= 25:
            found["Cholesterol"].append(("High", f"Cholesterol up {pct_chol:.0f}% vs recent baseline"))
        elif pct_chol >= 15:
            found["Cholesterol"].append(("Medium", f"Cholesterol up {pct_chol:.0f}% vs recent baseline"))

    alerts = []
    for metric, items in found.items():
        if not items:
            continue
        top = max(SEV_RANK[s] for s, _ in items)
        severity = next(s for s, r in SEV_RANK.items() if r == top)
        reasons = [reason for sev, reason in items if sev == severity]
        alerts.append({"metric": metric, "severity": severity, "reason": "; ".join(reasons)})
    return alerts


def evaluate_series(df: pd.DataFrame, last_n: int = 4) -> list[dict]:
    """Alerts for the last `last_n` readings of a patient (used when seeding)."""
    df = df.reset_index(drop=True)
    out = []
    for i in range(max(3, len(df) - last_n), len(df)):
        for a in evaluate_reading(df.iloc[:i], df.iloc[i]):
            out.append({**a, "alert_date": df.iloc[i]["recorded_on"]})
    return out

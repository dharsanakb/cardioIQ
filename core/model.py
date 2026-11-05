"""Risk model: shared preprocessing, prediction, categories and SHAP explanations."""
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "risk_model.joblib"

NUMERIC = ["Age", "RestingBP", "Cholesterol", "FastingBS", "MaxHR", "Oldpeak"]
CATEGORICAL = ["Sex", "ChestPainType", "RestingECG", "ExerciseAngina", "ST_Slope"]

# Cut-offs on the model's predicted probability (illustrative).
LOW_CUTOFF, HIGH_CUTOFF = 0.30, 0.65
RISK_COLORS = {"Low": "#2e9e6b", "Moderate": "#f0a020", "High": "#d64545"}
RISK_EMOJI = {"Low": "🟢", "Moderate": "🟠", "High": "🔴"}

SEX = {"M": "Male", "F": "Female"}
CHEST_PAIN = {"ATA": "Atypical angina", "NAP": "Non-anginal pain", "ASY": "Asymptomatic", "TA": "Typical angina"}
RESTING_ECG = {"Normal": "Normal", "ST": "ST-T abnormality", "LVH": "LV hypertrophy"}
EXERCISE_ANGINA = {"N": "No", "Y": "Yes"}
ST_SLOPE = {"Up": "Upsloping", "Flat": "Flat", "Down": "Downsloping"}
VALUE_LABELS = {
    "Sex": SEX, "ChestPainType": CHEST_PAIN, "RestingECG": RESTING_ECG,
    "ExerciseAngina": EXERCISE_ANGINA, "ST_Slope": ST_SLOPE,
}
NUMERIC_LABELS = {
    "Age": "Age", "RestingBP": "Resting blood pressure", "Cholesterol": "Cholesterol",
    "FastingBS": "Fasting blood sugar > 120", "MaxHR": "Max heart rate", "Oldpeak": "ST depression (oldpeak)",
}
CATEGORY_LABELS = {
    "Sex": "Sex", "ChestPainType": "Chest pain type", "RestingECG": "Resting ECG",
    "ExerciseAngina": "Exercise angina", "ST_Slope": "ST slope",
}


# ---------- preprocessing (shared by training and the app) ----------
def to_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Map database column names to the dataset's column names."""
    return pd.DataFrame({
        "Age": df["age"].values, "Sex": df["sex"].values, "ChestPainType": df["chest_pain"].values,
        "RestingBP": df["resting_bp"].values, "Cholesterol": df["cholesterol"].values,
        "FastingBS": df["fasting_bs"].values, "RestingECG": df["resting_ecg"].values,
        "MaxHR": df["max_hr"].values, "ExerciseAngina": df["exercise_angina"].values,
        "Oldpeak": df["oldpeak"].values, "ST_Slope": df["st_slope"].values,
    })


def encode(m: pd.DataFrame, columns=None) -> pd.DataFrame:
    X = pd.get_dummies(m[NUMERIC + CATEGORICAL], columns=CATEGORICAL, dtype=float)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0.0)
    return X.astype(float)


# ---------- model ----------
@lru_cache(maxsize=1)
def load_bundle() -> dict:
    return joblib.load(MODEL_PATH)


def _prepare(df: pd.DataFrame):
    b = load_bundle()
    m = to_model_frame(df).astype({c: float for c in ["RestingBP", "Cholesterol", "MaxHR", "Oldpeak"]})
    m = m.fillna(b["medians"])
    return m, encode(m, b["columns"])


def predict(df: pd.DataFrame) -> np.ndarray:
    _, X = _prepare(df)
    return load_bundle()["model"].predict_proba(X)[:, 1]


def categorize(p: float) -> str:
    return "Low" if p < LOW_CUTOFF else "Moderate" if p < HIGH_CUTOFF else "High"


def _label(col: str, row_value) -> str | None:
    if col in NUMERIC:
        return f"{NUMERIC_LABELS[col]}: {row_value:g}"
    for cat in CATEGORICAL:
        if col.startswith(cat + "_"):
            value = col[len(cat) + 1:]
            return f"{CATEGORY_LABELS[cat]}: {VALUE_LABELS[cat].get(value, value)}"
    return col


def explain(df_one: pd.DataFrame, top: int = 8) -> pd.DataFrame:
    """Per-patient feature contributions (SHAP, in log-odds). Positive = raises risk."""
    b = load_bundle()
    m, X = _prepare(df_one)
    try:
        import shap
        sv = shap.TreeExplainer(b["model"]).shap_values(X)
        sv = np.asarray(sv[1] if isinstance(sv, list) else sv)
        contrib = sv[..., 1][0] if sv.ndim == 3 else sv[0]
    except Exception:  # SHAP unavailable: fall back to global importances (no direction)
        contrib = b["model"].feature_importances_

    rows = []
    for col, c in zip(X.columns, contrib):
        if col in NUMERIC:
            rows.append((_label(col, m.iloc[0][col]), float(c)))
        elif X.iloc[0][col] == 1.0:  # only show the category the patient actually has
            rows.append((_label(col, None), float(c)))
    out = pd.DataFrame(rows, columns=["label", "contribution"])
    out = out.reindex(out["contribution"].abs().sort_values(ascending=False).index)
    return out.head(top).reset_index(drop=True)

"""Train the cardiac risk model. Run once from the project root:  python train_model.py

Expects data/heart.csv from Kaggle "Heart Failure Prediction" (fedesoriano).
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split

from core import model as M

DATA = Path("data/heart.csv")
if not DATA.exists():
    raise SystemExit("data/heart.csv not found. Download it from Kaggle (see README).")

df = pd.read_csv(DATA)
# In this dataset 0 means "not recorded" for these two columns.
df["Cholesterol"] = df["Cholesterol"].replace(0, np.nan)
df["RestingBP"] = df["RestingBP"].replace(0, np.nan)

y = df["HeartDisease"]
X_raw = df[M.NUMERIC + M.CATEGORICAL]
X_tr_raw, X_te_raw, y_tr, y_te = train_test_split(X_raw, y, test_size=0.2, stratify=y, random_state=42)

medians = X_tr_raw[M.NUMERIC].median().to_dict()  # from the training split only (no leakage)
X_tr = M.encode(X_tr_raw.fillna(medians))
columns = list(X_tr.columns)
X_te = M.encode(X_te_raw.fillna(medians), columns)

clf = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=3, subsample=0.8, random_state=42)
cv_auc = cross_val_score(clf, X_tr, y_tr, cv=5, scoring="roc_auc")
clf.fit(X_tr, y_tr)

proba = clf.predict_proba(X_te)[:, 1]
pred = (proba >= 0.5).astype(int)
metrics = {
    "accuracy": accuracy_score(y_te, pred),
    "precision": precision_score(y_te, pred),
    "recall": recall_score(y_te, pred),
    "f1": f1_score(y_te, pred),
    "roc_auc": roc_auc_score(y_te, proba),
    "cv_roc_auc_mean": float(cv_auc.mean()),
    "cv_roc_auc_std": float(cv_auc.std()),
    "n_train": len(X_tr),
    "n_test": len(X_te),
}
for k, v in metrics.items():
    print(f"{k:>16}: {v:.3f}" if isinstance(v, float) else f"{k:>16}: {v}")

Path("models").mkdir(exist_ok=True)
joblib.dump({"model": clf, "columns": columns, "medians": medians, "metrics": metrics,
             "dataset": "Heart Failure Prediction (Kaggle)"}, M.MODEL_PATH)
print(f"Saved model to {M.MODEL_PATH}")

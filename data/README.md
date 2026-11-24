# CardioIQ 🫀

**AI-assisted cardiac risk estimation and patient monitoring for clinical review.**

CardioIQ is a clinician-facing Streamlit prototype that combines a machine-learning cardiac risk model, longitudinal vitals tracking, a rule-based alert engine and an LLM-generated patient summary in one workspace.

**Live demo:** https://dharsanakb-cardioiq-app-bctk9r.streamlit.app/


> **Prototype for education and portfolio use only. Not a medical device, and not validated for clinical use.** All patients and vitals in the demo are simulated. See [Limitations](#limitations).


---

## Features

| Area | What it does |
|---|---|
| **Overview** | Patient list sorted by risk, with search, risk-level and status filters, summary metrics (total, high risk, open alerts, needs review) and an *Add patient* form. Selecting a row opens the patient profile. |
| **Risk assessment** | Model-estimated risk score on a gauge (Low / Moderate / High) with a per-patient SHAP explanation showing which factors raise or lower the estimate. |
| **Vitals & trends** | Latest readings compared with the patient's own recent baseline, a selectable trend chart (BP, heart rate, cholesterol) over 3, 6 or 12 months, and a form to record new readings. |
| **Alerts** | Rule-based alerts with plain-language reasons and severity (Low / Medium / High). Alerts can be marked reviewed. |
| **Reports** | Upload and download patient documents (PDF, PNG, JPG, CSV). |
| **History** | Timeline of clinical notes and system events. |
| **AI summary** | A short clinician-oriented summary of risk, key drivers, trends and open alerts. It uses an LLM when a key is configured and a template otherwise. |
| **Analytics** | Population view: risk distribution, risk by age band, alert patterns and the model's test performance. |
| **Doctor login** | Simple authentication gate in front of all clinical pages. |

---

## How it works

```
data/heart.csv ──► train_model.py ──► models/risk_model.joblib
                                              │
SQLite               ◄── core/db.py           ▼
   patients, vitals,      │            core/model.py  (predict + SHAP)
   alerts, reports,       ▼                   │
   history           core/service.py ◄────────┘
                          │
        core/alerts.py ───┤
        core/summary.py ──┤
                          ▼
              Streamlit views (views/*.py)
```

### Risk model

- **Data:** [Heart Failure Prediction Dataset](https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction) (Kaggle, fedesoriano): 918 patients, 11 clinical features, binary `HeartDisease` target.
- **Features:** Age, Sex, ChestPainType, RestingBP, Cholesterol, FastingBS, RestingECG, MaxHR, ExerciseAngina, Oldpeak, ST_Slope.
- **Preprocessing:** zeros in `Cholesterol` and `RestingBP` are treated as missing; missing values are median-imputed using the **training split only** (no leakage); categorical features are one-hot encoded.
- **Model:** `GradientBoostingClassifier` (200 trees, learning rate 0.05, max depth 3, subsample 0.8, `random_state=42`), 80/20 stratified split.
- **Explainability:** SHAP `TreeExplainer` for per-patient feature contributions.
- **Risk categories:** Low < 30%, Moderate 30 to 65%, High ≥ 65% of predicted probability. These cut-offs are illustrative.

**Held-out test performance** (n = 184, threshold 0.5):

| ROC-AUC | Accuracy | Precision | Recall |
|:---:|:---:|:---:|:---:|
| 0.93 | 0.88 | 0.89 | 0.88 |

Confusion matrix: 90 true positives, 12 false negatives, 11 false positives, 71 true negatives. Run `python train_model.py` to regenerate exact figures, including 5-fold cross-validated ROC-AUC.

### Alert engine

Rule-based on purpose, so every alert is fully explainable. Thresholds are **illustrative**, not clinical guidelines.

| Metric | Absolute rule | Change vs. patient's baseline* |
|---|---|---|
| Systolic BP | ≥ 140 Medium · ≥ 160 High | +12 Medium · +20 High |
| Heart rate | > 100 or < 50 Medium · > 120 or < 40 High | ±12 Medium · ±20 High |
| Cholesterol | ≥ 240 Medium · ≥ 280 High | +15% Medium · +25% High |

\*Baseline = mean of up to the 5 previous readings; requires at least 3 prior readings.

### AI summary

- Calls the [Groq](https://console.groq.com) API when `GROQ_API_KEY` is set (default model `openai/gpt-oss-120b`, configurable via `GROQ_MODEL`).
- Only **de-identified clinical values** are sent (age, sex, risk score, top factors, vitals, open alerts). No name or ID leaves the app.
- The prompt instructs the model to use only the supplied data and not to diagnose or prescribe.
- Without a key, or if the call fails, the app falls back to a template summary and labels the source.

### Demo data

On first start the app creates its tables and seeds **60 patients** sampled from the Kaggle dataset, with randomly generated names and **12 months of simulated vitals**. About 35% of patients get a recent deterioration so the alert engine has something to catch. Nothing here is real patient data.

---

## Project structure

```
cardioIQ/
├── app.py                  # Entry point: page config, auth gate, navigation
├── train_model.py          # Trains the risk model and saves it to models/
├── requirements.txt
├── core/
│   ├── model.py            # Preprocessing, prediction, risk categories, SHAP
│   ├── alerts.py           # Rule-based alert engine
│   ├── service.py          # Joins database and model (overview, per-patient risk)
│   ├── db.py               # SQLAlchemy layer (SQLite by default, PostgreSQL optional)
│   ├── seed.py             # Demo patients and simulated vitals
│   ├── summary.py          # AI summary with template fallback
│   ├── auth.py             # Demo-grade doctor login
│   └── config.py           # Secrets / environment variable access
├── views/                  # Streamlit pages: home, login, overview, patient, analytics
├── data/heart.csv          # Training data and seed source
├── models/risk_model.joblib
├── assets/style.css
└── .streamlit/
    ├── config.toml         # Theme
    └── secrets.toml.example
```

---

## Getting started

### 1. Install

```bash
git clone https://github.com/dharsanakb/cardioIQ.git
cd cardioIQ
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Train the model (optional)

A trained model is included in `models/`. To retrain it, for example after a scikit-learn version change:

```bash
python train_model.py
```

### 3. Run

```bash
streamlit run app.py
```

With no configuration the app runs in **demo mode**: sign in with username `doctor` and password `cardioiq123`. It uses a local SQLite file (`cardioiq.db`) that is created and seeded on first run.

---

## Configuration

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` (never commit the real file) or paste the values into the Streamlit Cloud **Secrets** panel. Environment variables of the same name also work.

```toml
# Optional: persistent database. Without it the app uses local SQLite,
# which resets on Streamlit Cloud restarts.
DATABASE_URL = "postgresql://user:password@host:5432/postgres?sslmode=require"

# Optional: enables LLM summaries. Without it a template summary is used.
GROQ_API_KEY = "your-key"
GROQ_MODEL   = "openai/gpt-oss-120b"

# Doctor accounts. Without this section the app runs in demo mode.
[users.drrao]
name = "Dr. Rao"
password_sha256 = "<hash>"
```

Generate a password hash with:

```bash
python -c "import hashlib; print(hashlib.sha256(b'your-password').hexdigest())"
```

### Deploy on Streamlit Community Cloud

1. Push the repo to GitHub.
2. Create a new app pointing at `app.py`.
3. Add your secrets in **Settings → Secrets**.
4. For persistent data, use a hosted PostgreSQL database (Supabase or Neon) via `DATABASE_URL`.

---

## Tech stack

Python · Streamlit · pandas · NumPy · scikit-learn · SHAP · Plotly · SQLAlchemy (SQLite / PostgreSQL) · joblib · Groq API

---

## Limitations

This project is a learning prototype. Please read these before drawing any conclusions from its output.

- **The score is not a 10-year risk score.** The training data comes from patients referred for cardiac evaluation (about 55% have disease), and the model estimates whether coronary disease is present, not future event risk. Established prognostic tools such as ASCVD, SCORE2 or QRISK are built for that purpose.
- **Inputs are weighted toward exercise-test findings** (ST slope, ST depression, exercise angina, peak heart rate) and chest pain type. Blood pressure and cholesterol have little influence on the score, so changes in monitored vitals do not move it much.
- **Small, pooled public dataset.** The data merges several sites, is male-dominated (about 79%) and has no external validation. Calibration and subgroup performance (for example in women) have not been assessed, and the test set is small.
- **Seeded demo patients are rows from the training data**, so population analytics look better than they would on new patients.
- **Alert thresholds are illustrative.** They are not derived from clinical guidelines, use systolic BP only and are not an emergency or acute-monitoring system.
- **Authentication is demo-grade.** There is no per-clinician access control, audit logging, encryption of stored reports or rate limiting. Do not use real patient data.

### Roadmap

- Add diastolic BP, LDL/HDL, smoking, diabetes status, family history and medications
- Handle "not assessed" inputs explicitly instead of defaulting to low-risk values
- Calibrate probabilities and choose risk cut-offs from sensitivity targets, with confidence intervals
- Reviewer, timestamp and action-taken fields on alert review
- Stronger authentication (salted hashing, role-based access, audit log)

---

## Dataset and citation

fedesoriano. (September 2021). *Heart Failure Prediction Dataset*. Kaggle. https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction

The dataset combines five heart disease datasets from the UCI Machine Learning Repository (Cleveland, Hungarian, Switzerland, Long Beach VA and Statlog). Check the licence terms on the Kaggle page before redistributing the data.

---

## Author

**Dharsana** · [@dharsanakb](https://github.com/dharsanakb)

## Disclaimer

CardioIQ is for educational purposes. It does not provide medical advice, diagnosis or treatment, and its output must not be used to make clinical decisions.
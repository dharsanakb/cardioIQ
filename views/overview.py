import streamlit as st

from core import db, model, service

st.title("Patient overview")
if msg := st.session_state.pop("flash", None):
    st.success(msg)


@st.dialog("Add new patient", width="large")
def add_patient_dialog():
    with st.form("new_patient"):
        name = st.text_input("Full name")
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age", 18, 100, 55)
        sex = c2.selectbox("Sex", list(model.SEX), format_func=model.SEX.get)
        chest = c3.selectbox("Chest pain type", list(model.CHEST_PAIN), format_func=model.CHEST_PAIN.get)
        c1, c2, c3 = st.columns(3)
        bp = c1.number_input("Systolic BP (mmHg)", 70, 250, 130)
        chol = c2.number_input("Cholesterol (mg/dL)", 80, 600, 210)
        hr = c3.number_input("Resting heart rate (bpm)", 30, 200, 72)
        c1, c2, c3 = st.columns(3)
        max_hr = c1.number_input("Max heart rate (exercise)", 60, 220, 150)
        ecg = c2.selectbox("Resting ECG", list(model.RESTING_ECG), format_func=model.RESTING_ECG.get)
        slope = c3.selectbox("ST slope", list(model.ST_SLOPE), format_func=model.ST_SLOPE.get)
        c1, c2, c3 = st.columns(3)
        oldpeak = c1.number_input("ST depression (oldpeak)", -3.0, 7.0, 0.0, step=0.1)
        angina = c2.selectbox("Exercise angina", list(model.EXERCISE_ANGINA), format_func=model.EXERCISE_ANGINA.get)
        fbs = c3.checkbox("Fasting blood sugar > 120 mg/dL")
        submitted = st.form_submit_button("Save patient", type="primary")
    if submitted:
        if not name.strip():
            st.error("Please enter a name.")
            return
        pid = db.add_patient({
            "name": name.strip(), "age": int(age), "sex": sex, "chest_pain": chest,
            "resting_bp": float(bp), "cholesterol": float(chol), "fasting_bs": int(fbs),
            "resting_ecg": ecg, "max_hr": float(max_hr), "exercise_angina": angina,
            "oldpeak": float(oldpeak), "st_slope": slope}, initial_hr=float(hr))
        st.session_state["selected_patient"] = pid
        st.session_state["flash"] = f"Added {name.strip()} (ID {pid}). Select the row to open the profile."
        st.rerun()


df = service.overview_table()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Patients", len(df))
m2.metric("High risk", int((df["risk_level"] == "High").sum()))
m3.metric("Open alerts", int(df["open_alerts"].sum()))
m4.metric("Needs review", int((df["status"] == "Needs review").sum()))

f1, f2, f3, f4 = st.columns([3, 2, 2, 1.4])
query = f1.text_input("Search", placeholder=" Search by name or ID", label_visibility="collapsed")
levels = f2.multiselect("Risk level", ["High", "Moderate", "Low"], placeholder="Risk level", label_visibility="collapsed")
statuses = f3.multiselect("Status", ["Needs review", "Monitoring", "Stable"], placeholder="Status", label_visibility="collapsed")
if f4.button(" Add patient", width="stretch"):
    add_patient_dialog()

view = df
if query:
    q = query.strip().lower()
    view = view[view["name"].str.lower().str.contains(q) | (view["id"].astype(str) == q)]
if levels:
    view = view[view["risk_level"].isin(levels)]
if statuses:
    view = view[view["status"].isin(statuses)]
view = view.sort_values("risk_score", ascending=False).reset_index(drop=True)

table = view.assign(
    risk_pct=(view["risk_score"] * 100).round(0),
    level=view["risk_level"].map(lambda x: f"{model.RISK_EMOJI[x]} {x}"),
    bp=view["latest_bp"].round(0), hr=view["latest_hr"].round(0), chol=view["latest_chol"].round(0),
    sex_label=view["sex"].map(model.SEX),
    last=view["last_reading"].dt.strftime("%d %b %Y"),
)[["id", "name", "age", "sex_label", "risk_pct", "level", "bp", "hr", "chol", "last", "open_alerts", "status"]]

event = st.dataframe(
    table, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
    column_config={
        "id": "ID", "name": "Patient", "age": "Age", "sex_label": "Sex",
        "risk_pct": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%d%%"),
        "level": "Risk level", "bp": "BP (mmHg)", "hr": "HR (bpm)", "chol": "Chol (mg/dL)",
        "last": "Last reading", "open_alerts": "Open alerts", "status": "Status",
    },
)

rows = event.selection.rows
if rows:
    chosen = table.iloc[rows[0]]
    if st.button(f"Open profile: {chosen['name']}", type="primary"):
        st.session_state["selected_patient"] = int(chosen["id"])
        st.switch_page("views/patient.py")
else:
    st.caption("Select a row to open a patient's profile.")

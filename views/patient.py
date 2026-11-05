from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import db, model, service, summary

SEV_BADGE = {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🟡 Low"}

pts = db.get_patients().sort_values("name")
if pts.empty:
    st.info("No patients yet. Add one from the Overview page.")
    st.stop()

ids = pts["id"].tolist()
names = dict(zip(pts["id"], pts["name"]))
default = st.session_state.get("selected_patient", ids[0])
if default not in ids:
    default = ids[0]
pid = st.selectbox("Patient", ids, index=ids.index(default), format_func=lambda i: f"{names[i]} (ID {i})")
st.session_state["selected_patient"] = pid

if msg := st.session_state.pop("flash", None):
    st.success(msg)

ctx = service.patient_risk(pid)
p, vit, score, cat, factors = ctx["patient"], ctx["vitals"], ctx["score"], ctx["category"], ctx["factors"]
alerts_all = db.get_alerts(pid)
alerts_open = alerts_all[~alerts_all["reviewed"]]

st.header(p["name"])
st.caption(f"ID {pid} · {p['age']} years · {model.SEX.get(p['sex'], p['sex'])}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Risk score", f"{score:.0%}")
m2.metric("Risk category", f"{model.RISK_EMOJI[cat]} {cat}")
m3.metric("Open alerts", len(alerts_open))
m4.metric("Last reading", vit.iloc[-1]["recorded_on"].strftime("%d %b %Y") if not vit.empty else "-")

tab_risk, tab_vitals, tab_alerts, tab_reports, tab_history, tab_ai = st.tabs(
    ["Risk Assessment", "Vitals & Trends", "Alerts", "Reports", "History", "AI Summary"])

# ---------------- Risk assessment ----------------
with tab_risk:
    left, right = st.columns([1, 2])
    with left:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score * 100, number={"suffix": "%"},
            title={"text": f"{cat} risk"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": model.RISK_COLORS[cat]},
                   "steps": [{"range": [0, model.LOW_CUTOFF * 100], "color": "#e6f4ec"},
                             {"range": [model.LOW_CUTOFF * 100, model.HIGH_CUTOFF * 100], "color": "#fdf1d9"},
                             {"range": [model.HIGH_CUTOFF * 100, 100], "color": "#fbe3e3"}]}))
        gauge.update_layout(height=280, margin=dict(l=20, r=20, t=60, b=10))
        st.plotly_chart(gauge, width="stretch")
    with right:
        st.markdown("**Key factors behind this estimate**")
        f = factors.sort_values("contribution")
        bar = go.Figure(go.Bar(
            x=f["contribution"], y=f["label"], orientation="h",
            marker_color=["#d64545" if v > 0 else "#2e9e6b" for v in f["contribution"]]))
        bar.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=30),
                          xaxis_title="← lowers risk | raises risk → (SHAP, log-odds)")
        st.plotly_chart(bar, width="stretch")
    with st.expander("Clinical inputs used by the model"):
        st.dataframe(pd.DataFrame({
            "Measure": ["Age", "Sex", "Chest pain type", "Systolic BP (latest)", "Cholesterol (latest)",
                        "Fasting blood sugar > 120", "Resting ECG", "Max heart rate", "Exercise angina",
                        "ST depression", "ST slope"],
            "Value": [p["age"], model.SEX.get(p["sex"]), model.CHEST_PAIN.get(p["chest_pain"]),
                      f"{p['resting_bp']:.0f} mmHg", f"{p['cholesterol']:.0f} mg/dL",
                      "Yes" if p["fasting_bs"] else "No", model.RESTING_ECG.get(p["resting_ecg"]),
                      f"{p['max_hr']:.0f} bpm", model.EXERCISE_ANGINA.get(p["exercise_angina"]),
                      p["oldpeak"], model.ST_SLOPE.get(p["st_slope"])],
        }).astype(str), hide_index=True, width="stretch")
    st.caption("Decision support only. The treating doctor makes the final clinical decision.")

# ---------------- Vitals & trends ----------------
with tab_vitals:
    metrics = [("systolic_bp", "Systolic BP (mmHg)"), ("heart_rate", "Resting heart rate (bpm)"),
               ("cholesterol", "Cholesterol (mg/dL)")]
    if len(vit) >= 2:
        latest, base = vit.iloc[-1], vit.iloc[:-1].tail(5)
        cols = st.columns(3)
        for col, (k, label) in zip(cols, metrics):
            col.metric(label, f"{latest[k]:.0f}", delta=f"{latest[k] - base[k].mean():+.0f} vs baseline",
                       delta_color="inverse")
        st.caption("Baseline = average of the patient's previous 5 readings.")

    period = st.radio("Period", ["3 months", "6 months", "12 months", "All"], index=2, horizontal=True)
    days = {"3 months": 90, "6 months": 180, "12 months": 365}.get(period)
    shown = vit if days is None else vit[vit["recorded_on"] >= pd.Timestamp(date.today()) - pd.Timedelta(days=days)]

    for k, label in metrics:
        fig = go.Figure(go.Scatter(x=shown["recorded_on"], y=shown[k], mode="lines+markers",
                                   line=dict(color="#0e7c86"), name=label))
        if len(shown) > 1:
            fig.add_hline(y=shown[k].mean(), line_dash="dot", line_color="#888",
                          annotation_text="period average", annotation_position="bottom right")
        fig.update_layout(title=label, height=260, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Record a new reading"):
        last = vit.iloc[-1] if not vit.empty else None
        with st.form("new_reading"):
            c1, c2, c3, c4 = st.columns(4)
            when = c1.date_input("Date", date.today())
            sbp = c2.number_input("Systolic BP", 60, 260, int(last["systolic_bp"]) if last is not None else 120)
            hr = c3.number_input("Heart rate", 30, 220, int(last["heart_rate"]) if last is not None else 72)
            chol = c4.number_input("Cholesterol", 80, 600, int(last["cholesterol"]) if last is not None else 200)
            if st.form_submit_button("Save reading", type="primary"):
                new = db.add_vitals(pid, when, float(sbp), float(hr), float(chol))
                st.session_state["flash"] = (
                    f"Reading saved. {len(new)} new alert(s) raised." if new else "Reading saved. No alerts raised.")
                st.rerun()

# ---------------- Alerts ----------------
with tab_alerts:
    if alerts_open.empty:
        st.success("No open alerts for this patient.")
    for a in alerts_open.itertuples():
        c1, c2, c3 = st.columns([1.2, 5, 1.5])
        c1.markdown(f"**{SEV_BADGE[a.severity]}**\n\n{a.alert_date:%d %b %Y}")
        c2.markdown(f"**{a.metric}**\n\n{a.reason}")
        if c3.button("Mark reviewed", key=f"rev_{a.id}"):
            db.mark_reviewed(int(a.id))
            st.rerun()
        st.divider()
    reviewed = alerts_all[alerts_all["reviewed"]]
    if not reviewed.empty:
        with st.expander(f"Reviewed alerts ({len(reviewed)})"):
            st.dataframe(reviewed.assign(date=reviewed["alert_date"].dt.strftime("%d %b %Y"))[
                ["date", "severity", "metric", "reason"]], hide_index=True, width="stretch")

# ---------------- Reports ----------------
with tab_reports:
    upload = st.file_uploader("Upload a report (PDF, image, CSV)", type=["pdf", "png", "jpg", "jpeg", "csv"],
                              key=f"upload_{pid}")
    if upload is not None and st.button("Save report", type="primary"):
        db.add_report(pid, upload.name, upload.getvalue())
        st.session_state["flash"] = f"Saved {upload.name}."
        st.rerun()
    reports = db.list_reports(pid)
    if reports.empty:
        st.caption("No reports uploaded yet.")
    for r in reports.itertuples():
        c1, c2 = st.columns([4, 1])
        c1.write(f" **{r.filename}** · uploaded {pd.Timestamp(r.uploaded_at):%d %b %Y}")
        c2.download_button("Download", db.get_report_content(int(r.id)), file_name=r.filename, key=f"dl_{r.id}")

# ---------------- History ----------------
with tab_history:
    with st.form("new_note", clear_on_submit=True):
        note = st.text_area("Add a clinical note", height=80)
        if st.form_submit_button("Add note") and note.strip():
            db.add_history(pid, note.strip())
            st.rerun()
    for h in db.get_history(pid).itertuples():
        st.markdown(f"**{h.event_date:%d %b %Y}** — {h.note}")

# ---------------- AI summary ----------------
with tab_ai:
    key = f"summary_{pid}"
    if st.button("Generate summary", type="primary"):
        with st.spinner("Writing summary..."):
            st.session_state[key] = summary.generate(p, score, cat, factors, vit, alerts_all)
    if key in st.session_state:
        text, source = st.session_state[key]
        st.markdown(text)
        st.caption(f"Source: {source}. Review before relying on it; the doctor makes the final decision.")
    else:
        st.caption("Click to generate a short summary of risk, trends and alerts.")

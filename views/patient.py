
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import db, model, service, summary

# CONFIGURATION
SEVERITY_BADGE = {
    "High": "🔴 High",
    "Medium": "🟠 Medium",
    "Low": "🟡 Low",
}

VITAL_METRICS = {
    "Blood Pressure": {
        "column": "systolic_bp",
        "label": "Systolic BP",
        "unit": "mmHg",
    },
    "Heart Rate": {
        "column": "heart_rate",
        "label": "Heart Rate",
        "unit": "bpm",
    },
    "Cholesterol": {
        "column": "cholesterol",
        "label": "Cholesterol",
        "unit": "mg/dL",
    },
}

# PAGE STYLING

st.markdown(
    """
    <style>

    /* Main content */

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        max-width: 1500px;
    }

    /* Patient heading */

    .patient-heading {
        font-size: 30px;
        font-weight: 700;
        color: #172B3A;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .patient-subheading {
        color: #788692;
        font-size: 14px;
        margin-top: 5px;
    }

    /* Section headings */

    .section-label {
        color: #788692;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }

    /* Metric cards */

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5EBEF;
        border-radius: 12px;
        padding: 10px 12px;
        min-height: 100px;
    }

    div[data-testid="stMetricLabel"] {
        color: #647482;
        font-size: 13px;
    }

    div[data-testid="stMetricValue"] {
        color: #183247;
        font-size: 25px;
        font-weight: 650;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 11px;
    }

    /* Tabs */

    button[data-baseweb="tab"] {
        font-size: 13px;
        font-weight: 600;
        padding-left: 13px;
        padding-right: 13px;
    }

    /* Expanders */

    div[data-testid="stExpander"] {
        border: 1px solid #E5EBEF;
        border-radius: 10px;
    }

    /* Buttons */

    div.stButton > button {
        border-radius: 8px;
    }

    /* Chart spacing */

    div[data-testid="stPlotlyChart"] {
        margin-bottom: 0;
    }

    /* Captions */

    .stCaption {
        color: #788692;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# LOAD PATIENTS

patients = db.get_patients().sort_values("name")

if patients.empty:
    st.info(
        "No patients available. Add a patient from the Overview page."
    )
    st.stop()

patient_ids = patients["id"].tolist()

patient_names = dict(
    zip(patients["id"], patients["name"])
)

default_patient = st.session_state.get(
    "selected_patient",
    patient_ids[0]
)

if default_patient not in patient_ids:
    default_patient = patient_ids[0]


# PATIENT SELECTOR

header_col, selector_col = st.columns(
    [2.5, 1.5],
    vertical_alignment="center"
)

with selector_col:

    selected_id = st.selectbox(
        "Select patient",
        patient_ids,
        index=patient_ids.index(default_patient),
        format_func=lambda x: (
            f"{patient_names[x]} · ID {x}"
        ),
        key="patient_selector",
    )

pid = selected_id

st.session_state["selected_patient"] = pid


# LOAD PATIENT DATA

if msg := st.session_state.pop("flash", None):
    st.success(msg)

ctx = service.patient_risk(pid)

patient = ctx["patient"]
vitals = ctx["vitals"]
risk_score = ctx["score"]
risk_category = ctx["category"]
factors = ctx["factors"]

alerts_all = db.get_alerts(pid)

alerts_open = alerts_all[
    ~alerts_all["reviewed"]
]

latest = (
    vitals.iloc[-1]
    if not vitals.empty
    else None
)

# COMPACT PATIENT HEADER

with header_col:

    st.markdown(
        f"""
        <div class="patient-heading">
            {patient['name']}
        </div>
        <div class="patient-subheading">
            Patient ID: {pid}
            &nbsp;·&nbsp;
            {patient['age']} years
            &nbsp;·&nbsp;
            {model.SEX.get(patient['sex'], patient['sex'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    '<div class="section-label">PATIENT OVERVIEW</div>',
    unsafe_allow_html=True,
)

# PATIENT SNAPSHOT CARDS

c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    st.metric(
        "Cardiac risk score",
        f"{risk_score:.0%}",
    )

with c2:
    st.metric(
        "Risk category",
        str(risk_category),
    )

with c3:
    st.metric(
        "Open alerts",
        len(alerts_open),
    )

with c4:
    st.metric(
        "Latest reading",
        (
            latest["recorded_on"].strftime("%d %b %Y")
            if latest is not None
            else "Not available"
        ),
    )

# PATIENT TABS

(
    tab_risk,
    tab_vitals,
    tab_alerts,
    tab_reports,
    tab_history,
    tab_ai,
) = st.tabs(
    [
        "Risk Assessment",
        "Vitals & Trends",
        f"Alerts ({len(alerts_open)})",
        "Reports",
        "History",
        "AI Summary",
    ]
)

# 1. RISK ASSESSMENT

with tab_risk:

    st.subheader("Cardiac risk assessment")

    st.caption(
        "Model-generated estimate based on the patient's "
        "available clinical inputs."
    )

    risk_col, factors_col = st.columns(
        [0.9, 1.6],
        gap="large",
    )

    # RISK GAUGE

    with risk_col:

        st.markdown("**Overall risk estimate**")

        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=risk_score * 100,
                number={
                    "suffix": "%",
                    "font": {
                        "size": 38,
                        "color": "#183247",
                    },
                },
                gauge={
                    "axis": {
                        "range": [0, 100],
                        "tickwidth": 1,
                        "tickfont": {
                            "size": 10,
                        },
                    },
                    "bar": {
                        "color": model.RISK_COLORS[risk_category],
                        "thickness": 0.25,
                    },
                    "bgcolor": "white",
                    "borderwidth": 0,
                    "steps": [
                        {
                            "range": [
                                0,
                                model.LOW_CUTOFF * 100,
                            ],
                            "color": "#E6F4EC",
                        },
                        {
                            "range": [
                                model.LOW_CUTOFF * 100,
                                model.HIGH_CUTOFF * 100,
                            ],
                            "color": "#FDF1D9",
                        },
                        {
                            "range": [
                                model.HIGH_CUTOFF * 100,
                                100,
                            ],
                            "color": "#FBE3E3",
                        },
                    ],
                },
            )
        )

        gauge.update_layout(
            height=205,
            margin=dict(
                l=10,
                r=10,
                t=15,
                b=5,
            ),
            paper_bgcolor="white",
            font=dict(color="#142C43"),
        )

        st.plotly_chart(
            gauge,
            width="stretch",
            config={
                "displayModeBar": False,
            },
        )

        st.markdown(
            f"**Estimated category: {risk_category}**"
        )

    # FEATURE CONTRIBUTIONS

    with factors_col:

        st.markdown(
            "**Key factors behind this estimate**"
        )

        if not factors.empty:

            factor_data = (
                factors.assign(
                    abs_contribution=(
                        factors["contribution"].abs()
                    )
                )
                .nlargest(
                    6,
                    "abs_contribution",
                )
                .sort_values(
                    "contribution",
                    ascending=True,
                )
            )

            colors = [
                "#D64545" if value > 0 else "#2E9E6B"
                for value in factor_data["contribution"]
            ]

            factor_chart = go.Figure(
                go.Bar(
                    x=factor_data["contribution"],
                    y=factor_data["label"],
                    orientation="h",
                    marker_color=colors,
                    hovertemplate=(
                        "%{y}<br>"
                        "Contribution: %{x:.3f}"
                        "<extra></extra>"
                    ),
                )
            )

            factor_chart.update_layout(
                height=235,
                margin=dict(
                    l=8,
                    r=12,
                    t=5,
                    b=30,
                ),
                xaxis_title="Feature contribution",
                yaxis_title=None,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(
                    color="#536575",
                    size=11,
                ),
            )

            factor_chart.update_xaxes(
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor="#AAB5BE",
                showgrid=True,
                gridcolor="#EDF1F4",
            )

            st.plotly_chart(
                factor_chart,
                width="stretch",
                config={
                    "displayModeBar": False,
                },
            )

            st.caption(
                "Red: increases model estimate · "
                "Green: decreases model estimate."
            )

        else:

            st.info(
                "Feature contribution information is unavailable."
            )

# 2. VITALS AND TRENDS

with tab_vitals:

    st.subheader("Vitals & trends")

    if vitals.empty:

        st.info(
            "No vital readings have been recorded for this patient."
        )

    else:

        latest = vitals.iloc[-1]

        # LATEST READINGS

        st.markdown("**Latest recorded readings**")

        previous = (
            vitals.iloc[:-1].tail(5)
            if len(vitals) >= 2
            else None
        )

        metric_columns = st.columns(3)

        vital_cards = [
            (
                "systolic_bp",
                "Blood pressure",
                "mmHg",
            ),
            (
                "heart_rate",
                "Heart rate",
                "bpm",
            ),
            (
                "cholesterol",
                "Cholesterol",
                "mg/dL",
            ),
        ]

        for col, (key, label, unit) in zip(
            metric_columns,
            vital_cards,
        ):

            delta = None

            if previous is not None:

                baseline = previous[key].mean()

                difference = latest[key] - baseline

                delta = (
                    f"{difference:+.0f} {unit} vs baseline"
                )

            col.metric(
                label,
                f"{latest[key]:.0f} {unit}",
                delta=delta,
                delta_color="off",
            )

        if previous is not None:

            st.caption(
                "Baseline comparison uses the average "
                "of up to five previous readings."
            )


        # SELECTABLE TREND CHART

        st.markdown("**Historical trend analysis**")

        control_col, period_col = st.columns([2, 1])

        with control_col:

            selected_metric = st.selectbox(
                "Select vital",
                list(VITAL_METRICS.keys()),
                key=f"vital_metric_{pid}",
            )

        with period_col:

            selected_period = st.selectbox(
                "Time period",
                [
                    "3 months",
                    "6 months",
                    "12 months",
                    "All records",
                ],
                index=2,
                key=f"vital_period_{pid}",
            )

        days = {
            "3 months": 90,
            "6 months": 180,
            "12 months": 365,
            "All records": None,
        }[selected_period]

        shown = vitals.copy()

        if days is not None:

            cutoff = (
                pd.Timestamp(date.today())
                - pd.Timedelta(days=days)
            )

            shown = shown[
                shown["recorded_on"] >= cutoff
            ]

        metric_info = VITAL_METRICS[selected_metric]

        column = metric_info["column"]
        label = metric_info["label"]
        unit = metric_info["unit"]

        if shown.empty:

            st.warning(
                "No readings are available for the selected time period."
            )

        else:

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=shown["recorded_on"],
                    y=shown[column],
                    mode="lines+markers",
                    name=label,
                    line=dict(
                        color="#087F8C",
                        width=3,
                    ),
                    marker=dict(size=7),
                    fill="tozeroy",
                    fillcolor="rgba(8,127,140,0.08)",
                    hovertemplate=(
                        "%{x|%d %b %Y}<br>"
                        + label
                        + ": %{y:.1f} "
                        + unit
                        + "<extra></extra>"
                    ),
                )
            )

            if len(shown) > 1:

                average = shown[column].mean()

                fig.add_hline(
                    y=average,
                    line_dash="dot",
                    line_color="#E0A12B",
                    annotation_text=(
                        f"Average: {average:.1f}"
                    ),
                    annotation_position="bottom right",
                )

            fig.update_layout(
                height=240,
                margin=dict(
                    l=5,
                    r=5,
                    t=10,
                    b=5,
                ),
                showlegend=False,
                xaxis_title=None,
                yaxis_title=unit,
                hovermode="x unified",
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(
                    color="#142C43",
                    size=11,
                ),
            )

            fig.update_xaxes(
                showgrid=False
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={
                    "displayModeBar": False,
                },
            )

            st.caption(
                f"{len(shown)} readings displayed for "
                f"{selected_metric.lower()}."
            )

        # READING HISTORY

        with st.expander(
            f"View all recorded readings ({len(vitals)})"
        ):

            history_table = vitals.sort_values(
                "recorded_on",
                ascending=False,
            ).copy()

            history_table["Date"] = (
                history_table["recorded_on"].dt.strftime(
                    "%d %b %Y"
                )
            )

            history_table = history_table[
                [
                    "Date",
                    "systolic_bp",
                    "heart_rate",
                    "cholesterol",
                ]
            ].rename(
                columns={
                    "systolic_bp": "BP (mmHg)",
                    "heart_rate": "Heart rate (bpm)",
                    "cholesterol": "Cholesterol (mg/dL)",
                }
            )

            st.dataframe(
                history_table,
                hide_index=True,
                width="stretch",
            )

    # RECORD NEW READING

    with st.expander("＋ Record a new reading"):

        latest = (
            vitals.iloc[-1]
            if not vitals.empty
            else None
        )

        with st.form(f"new_reading_{pid}"):

            c1, c2, c3, c4 = st.columns(4)

            recorded_date = c1.date_input(
                "Reading date",
                date.today(),
            )

            sbp = c2.number_input(
                "Systolic BP (mmHg)",
                min_value=60,
                max_value=260,
                value=(
                    int(latest["systolic_bp"])
                    if latest is not None
                    else 120
                ),
            )

            hr = c3.number_input(
                "Heart rate (bpm)",
                min_value=30,
                max_value=220,
                value=(
                    int(latest["heart_rate"])
                    if latest is not None
                    else 72
                ),
            )

            cholesterol = c4.number_input(
                "Cholesterol (mg/dL)",
                min_value=80,
                max_value=600,
                value=(
                    int(latest["cholesterol"])
                    if latest is not None
                    else 200
                ),
            )

            submitted = st.form_submit_button(
                "Save reading",
                type="primary",
                width="stretch",
            )

            if submitted:

                if (
                    latest is not None
                    and pd.Timestamp(recorded_date)
                    < latest["recorded_on"]
                ):

                    st.error(
                        "The reading date cannot be earlier "
                        "than the latest recorded reading."
                    )

                else:

                    new_alerts = db.add_vitals(
                        pid,
                        recorded_date,
                        float(sbp),
                        float(hr),
                        float(cholesterol),
                    )

                    st.session_state["flash"] = (
                        f"Reading saved. {len(new_alerts)} "
                        "new alert(s) generated."
                        if new_alerts
                        else "Reading saved successfully."
                    )

                    st.rerun()

# 3. ALERTS

with tab_alerts:

    st.subheader("Patient alerts")

    total_open = len(alerts_open)

    if total_open == 0:

        st.success(
            "No open alerts for this patient."
        )

    else:

        st.caption(
            f"{total_open} alert(s) require review."
        )

        for alert in alerts_open.itertuples():

            with st.container(border=True):

                c1, c2, c3 = st.columns(
                    [1.2, 4, 1.3]
                )

                with c1:

                    st.markdown(
                        f"**{SEVERITY_BADGE.get(alert.severity, alert.severity)}**"
                    )

                    st.caption(
                        alert.alert_date.strftime("%d %b %Y")
                    )

                with c2:

                    st.markdown(
                        f"**{alert.metric}**"
                    )

                    st.write(
                        alert.reason
                    )

                with c3:

                    if st.button(
                        "Mark reviewed",
                        key=f"review_{alert.id}",
                        width="stretch",
                    ):

                        db.mark_reviewed(
                            int(alert.id)
                        )

                        st.session_state["flash"] = (
                            "Alert marked as reviewed."
                        )

                        st.rerun()

    reviewed = alerts_all[
        alerts_all["reviewed"]
    ]

    with st.expander(
        f"Reviewed alerts ({len(reviewed)})"
    ):

        if reviewed.empty:

            st.caption(
                "No reviewed alerts."
            )

        else:

            reviewed_table = reviewed.copy()

            reviewed_table["Date"] = (
                reviewed_table["alert_date"].dt.strftime(
                    "%d %b %Y"
                )
            )

            st.dataframe(
                reviewed_table[
                    [
                        "Date",
                        "severity",
                        "metric",
                        "reason",
                    ]
                ],
                hide_index=True,
                width="stretch",
            )

# 4. REPORTS

with tab_reports:

    st.subheader("Medical reports")

    reports = db.list_reports(pid)

    with st.expander("＋ Upload a new report"):

        upload = st.file_uploader(
            "Choose a report",
            type=[
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "csv",
            ],
            key=f"upload_{pid}",
        )

        if upload is not None:

            st.caption(
                f"Selected file: {upload.name}"
            )

            if st.button(
                "Save report",
                type="primary",
                key=f"save_report_{pid}",
            ):

                db.add_report(
                    pid,
                    upload.name,
                    upload.getvalue(),
                )

                st.session_state["flash"] = (
                    f"Report {upload.name} uploaded successfully."
                )

                st.rerun()

    st.markdown(
        f"**Uploaded reports ({len(reports)})**"
    )

    if reports.empty:

        st.info(
            "No reports have been uploaded for this patient."
        )

    else:

        for report in reports.itertuples():

            with st.container(border=True):

                c1, c2 = st.columns([4, 1])

                with c1:

                    st.markdown(
                        f"📄 **{report.filename}**"
                    )

                    st.caption(
                        "Uploaded "
                        + pd.Timestamp(
                            report.uploaded_at
                        ).strftime("%d %b %Y")
                    )

                with c2:

                    st.download_button(
                        "Download",
                        data=db.get_report_content(
                            int(report.id)
                        ),
                        file_name=report.filename,
                        key=f"download_{report.id}",
                        width="stretch",
                    )


# 5. PATIENT HISTORY

with tab_history:

    st.subheader("Clinical history")

    with st.expander("＋ Add a clinical note"):

        with st.form(
            f"new_note_{pid}",
            clear_on_submit=True,
        ):

            note_date = st.date_input(
                "Date",
                date.today(),
            )

            note = st.text_area(
                "Clinical note",
                placeholder=(
                    "Enter relevant medical history "
                    "or observations..."
                ),
                height=100,
            )

            if st.form_submit_button(
                "Save note",
                type="primary",
            ):

                if note.strip():

                    db.add_history(
                        pid,
                        note.strip(),
                        note_date,
                    )

                    st.session_state["flash"] = (
                        "Clinical note added."
                    )

                    st.rerun()

                else:

                    st.warning(
                        "Please enter a note."
                    )

    history = db.get_history(pid)

    if history.empty:

        st.info(
            "No clinical history recorded."
        )

    else:

        st.markdown(
            f"**Patient timeline · {len(history)} entries**"
        )

        for item in history.itertuples():

            with st.container(border=True):

                st.caption(
                    item.event_date.strftime("%d %b %Y")
                )

                st.write(
                    item.note
                )

# 6. AI SUMMARY

with tab_ai:

    st.subheader("AI-assisted patient summary")

    st.caption(
        "A concise overview of the patient's risk estimate, "
        "vital trends and alerts."
    )

    summary_key = f"summary_{pid}"

    if st.button(
        "Generate patient summary",
        type="primary",
        key=f"generate_summary_{pid}",
    ):

        with st.spinner(
            "Generating patient summary..."
        ):

            st.session_state[summary_key] = summary.generate(
                patient,
                risk_score,
                risk_category,
                factors,
                vitals,
                alerts_all,
            )

    if summary_key in st.session_state:

        generated_text, source = (
            st.session_state[summary_key]
        )

        with st.container(border=True):

            st.markdown(
                generated_text
            )

        st.caption(
            f"Source: {source}. Review the generated "
            "summary before using it in clinical "
            "decision-making."
        )


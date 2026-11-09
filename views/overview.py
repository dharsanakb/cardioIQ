
import streamlit as st

from core import db, model, service


# PAGE SPACING AND STYLING

st.markdown(
    """
    <style>
    /* Proper page spacing */
    .stMainBlockContainer {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }

    /* Keep page headings fully visible */
    h1 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        line-height: 1.3 !important;
        padding-top: 0 !important;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5ebef;
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* Patient table */
    div[data-testid="stDataFrame"] {
        border: 1px solid #e5ebef;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# PAGE HEADER

st.title("Patient Overview")

st.caption(
    "Monitor patient risk, review alerts and access patient records."
)

if msg := st.session_state.pop("flash", None):
    st.success(msg)


# ADD PATIENT DIALOG


@st.dialog("Add New Patient", width="large")
def add_patient_dialog():

    st.markdown("""
    <style>
    /* Compact dialog dimensions */
    [data-testid="stDialog"] [role="dialog"] {
        width: min(850px, 92vw) !important;
        max-width: 850px !important;
        max-height: 88vh !important;
        overflow-y: auto !important;
        border-radius: 14px !important;
    }

    /* Reduce dialog content spacing */
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {
        gap: 0.45rem !important;
    }

    /* Remove unnecessary inner card styling */
    [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        background: transparent !important;
    }

    /* Compact labels */
    [data-testid="stDialog"] label {
        font-size: 0.88rem !important;
    }

    /* Compact inputs */
    [data-testid="stDialog"] input {
        min-height: 38px !important;
    }

    /* Save button */
    [data-testid="stDialog"] .stFormSubmitButton button {
        background: #087F8C !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 650 !important;
        min-height: 40px !important;
    }

    [data-testid="stDialog"] .stFormSubmitButton button:hover {
        background: #066A75 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.form("new_patient"):

        name = st.text_input("Full name")

        c1, c2, c3 = st.columns(3)

        age = c1.number_input("Age", 18, 100, 55)

        sex = c2.selectbox(
            "Sex",
            list(model.SEX),
            format_func=model.SEX.get
        )

        chest = c3.selectbox(
            "Chest pain type",
            list(model.CHEST_PAIN),
            format_func=model.CHEST_PAIN.get
        )

        c1, c2, c3 = st.columns(3)

        bp = c1.number_input("Systolic BP (mmHg)", 70, 250, 130)
        chol = c2.number_input("Cholesterol (mg/dL)", 80, 600, 210)
        hr = c3.number_input("Resting heart rate (bpm)", 30, 200, 72)

        c1, c2, c3 = st.columns(3)

        max_hr = c1.number_input("Max heart rate", 60, 220, 150)

        ecg = c2.selectbox(
            "Resting ECG",
            list(model.RESTING_ECG),
            format_func=model.RESTING_ECG.get
        )

        slope = c3.selectbox(
            "ST slope",
            list(model.ST_SLOPE),
            format_func=model.ST_SLOPE.get
        )

        c1, c2, c3 = st.columns(3)

        oldpeak = c1.number_input(
            "ST depression (oldpeak)",
            -3.0, 7.0, 0.0, step=0.1
        )

        angina = c2.selectbox(
            "Exercise angina",
            list(model.EXERCISE_ANGINA),
            format_func=model.EXERCISE_ANGINA.get
        )

        fbs = c3.checkbox("Fasting blood sugar > 120 mg/dL")

        st.write("")

        submitted = st.form_submit_button(
            "Save Patient",
            type="primary",
            width="stretch"
        )

    if submitted:

        if not name.strip():
            st.error("Please enter a patient name.")
            return

        pid = db.add_patient({
            "name": name.strip(),
            "age": int(age),
            "sex": sex,
            "chest_pain": chest,
            "resting_bp": float(bp),
            "cholesterol": float(chol),
            "fasting_bs": int(fbs),
            "resting_ecg": ecg,
            "max_hr": float(max_hr),
            "exercise_angina": angina,
            "oldpeak": float(oldpeak),
            "st_slope": slope
        }, initial_hr=float(hr))

        st.session_state["selected_patient"] = pid
        st.session_state["flash"] = (
            f"Patient {name.strip()} added successfully."
        )

        st.rerun()



# LOAD PATIENT DATA

df = service.overview_table()

# TOP-LEVEL METRICS

total = len(df)

high = int(
    (df["risk_level"] == "High").sum()
)

open_alerts = int(
    df["open_alerts"].sum()
)

needs_review = int(
    (df["status"] == "Needs review").sum()
)

m1, m2, m3, m4 = st.columns(4)

m1.metric("Total patients", total)

m2.metric("High risk", high)

m3.metric("Open alerts", open_alerts)

m4.metric("Needs review", needs_review)


# ============================================================
# SEARCH AND FILTERS
# ============================================================

left, middle, right = st.columns(
    [3, 1.5, 1.5]
)

query = left.text_input(
    "Search patients",
    placeholder="Search by patient name or ID",
)

levels = middle.multiselect(
    "Risk level",
    ["High", "Moderate", "Low"],
    placeholder="All risk levels",
)

statuses = right.multiselect(
    "Patient status",
    ["Needs review", "Monitoring", "Stable"],
    placeholder="All statuses",
)


# ============================================================
# ADD PATIENT ACTION
# ============================================================

_, action_col = st.columns([5, 1])

with action_col:

    if st.button(
        "＋ Add patient",
        type="primary",
        width="stretch",
    ):
        add_patient_dialog()


# ============================================================
# FILTER PATIENT RECORDS
# ============================================================

view = df.copy()

if query:

    q = query.strip().lower()

    view = view[
        view["name"].str.lower().str.contains(
            q,
            na=False,
        )
        | (
            view["id"].astype(str) == q
        )
    ]

if levels:

    view = view[
        view["risk_level"].isin(levels)
    ]

if statuses:

    view = view[
        view["status"].isin(statuses)
    ]

view = (
    view.sort_values(
        "risk_score",
        ascending=False,
    )
    .reset_index(drop=True)
)


# ============================================================
# PATIENT LIST
# ============================================================

st.subheader("Patient list")

st.caption(
    f"Showing {len(view)} of {total} patients · "
    "Highest risk first"
)


if view.empty:

    st.info(
        "No patients match the selected filters."
    )

else:

    table = view.assign(
        risk_pct=(
            view["risk_score"] * 100
        ).round(0),

        bp=view["latest_bp"].round(0),

        hr=view["latest_hr"].round(0),

        last=(
            view["last_reading"]
            .dt.strftime("%d %b %Y")
            .fillna("No reading")
        ),
    )[
        [
            "id",
            "name",
            "age",
            "risk_pct",
            "risk_level",
            "bp",
            "hr",
            "open_alerts",
            "status",
            "last",
        ]
    ]


    event = st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key="patient_table",
        column_config={

            "id": st.column_config.NumberColumn(
                "ID",
                width="small",
            ),

            "name": st.column_config.TextColumn(
                "Patient Name",
                width="medium",
            ),

            "age": st.column_config.NumberColumn(
                "Age",
                width="small",
            ),

            "risk_pct": st.column_config.ProgressColumn(
                "Risk Score",
                min_value=0,
                max_value=100,
                format="%d%%",
            ),

            "risk_level": st.column_config.TextColumn(
                "Risk Level",
            ),

            "bp": st.column_config.NumberColumn(
                "BP (mmHg)",
                format="%.0f",
            ),

            "hr": st.column_config.NumberColumn(
                "Heart Rate",
                format="%.0f",
            ),

            "open_alerts": st.column_config.NumberColumn(
                "Alerts",
            ),

            "status": st.column_config.TextColumn(
                "Patient Status",
            ),

            "last": st.column_config.TextColumn(
                "Last Reading",
            ),
        },
    )

    # --------------------------------------------------------
    # AUTOMATIC NAVIGATION ON ROW SELECTION
    # --------------------------------------------------------

    selected_rows = event.selection.rows

    if selected_rows:

        selected_row = table.iloc[
            selected_rows[0]
        ]

        selected_patient_id = int(
            selected_row["id"]
        )

        st.session_state["selected_patient"] = (
            selected_patient_id
        )

        st.switch_page(
            "views/patient.py"
        )

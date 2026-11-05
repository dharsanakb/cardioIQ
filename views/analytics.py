import pandas as pd
import plotly.express as px
import streamlit as st

from core import db, model, service

st.title("Population analytics")

df = service.overview_table()
al = db.get_alerts()
order = ["Low", "Moderate", "High"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Patients", len(df))
m2.metric("Average risk score", f"{df['risk_score'].mean():.0%}")
m3.metric("High-risk share", f"{(df['risk_level'] == 'High').mean():.0%}")
m4.metric("Open alerts", int((~al["reviewed"]).sum()) if not al.empty else 0)

st.subheader("Risk distribution")
c1, c2 = st.columns(2)
counts = df["risk_level"].value_counts().reindex(order, fill_value=0).rename_axis("Risk level").reset_index(name="Patients")
c1.plotly_chart(px.bar(counts, x="Risk level", y="Patients", color="Risk level",
                       color_discrete_map=model.RISK_COLORS, title="Patients by risk category")
                .update_layout(showlegend=False), width="stretch")
bands = df.assign(**{"Age band": pd.cut(df["age"], [0, 39, 49, 59, 69, 120],
                                         labels=["<40", "40-49", "50-59", "60-69", "70+"])})
by_age = bands.groupby(["Age band", "risk_level"], observed=True).size().reset_index(name="Patients")
c2.plotly_chart(px.bar(by_age, x="Age band", y="Patients", color="risk_level", color_discrete_map=model.RISK_COLORS,
                       category_orders={"risk_level": order}, title="Risk category by age band")
                .update_layout(legend_title_text="Risk"), width="stretch")

st.subheader("Alert patterns")
if al.empty:
    st.info("No alerts recorded yet.")
else:
    c1, c2 = st.columns(2)
    by_metric = al.groupby(["metric", "severity"]).size().reset_index(name="Alerts")
    c1.plotly_chart(px.bar(by_metric, x="metric", y="Alerts", color="severity", title="Alerts by type and severity",
                           color_discrete_map={"High": "#d64545", "Medium": "#f0a020", "Low": "#e8d44d"})
                    .update_layout(xaxis_title=None), width="stretch")
    monthly = al.assign(month=al["alert_date"].dt.to_period("M").dt.to_timestamp()).groupby("month").size().reset_index(name="Alerts")
    c2.plotly_chart(px.line(monthly, x="month", y="Alerts", markers=True, title="Alerts per month")
                    .update_layout(xaxis_title=None), width="stretch")

st.subheader("Model performance")
metrics = model.load_bundle()["metrics"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("ROC-AUC (test)", f"{metrics['roc_auc']:.2f}")
k2.metric("Accuracy", f"{metrics['accuracy']:.2f}")
k3.metric("Recall", f"{metrics['recall']:.2f}")
k4.metric("Precision", f"{metrics['precision']:.2f}")
st.caption(f"Gradient boosting on the Kaggle Heart Failure Prediction dataset · {metrics['n_train']} training and "
           f"{metrics['n_test']} test rows · 5-fold CV ROC-AUC {metrics['cv_roc_auc_mean']:.2f} ± {metrics['cv_roc_auc_std']:.2f}. "
           "Small public dataset: not validated for clinical use.")

"""AI summary for the doctor. Uses the Groq API when a key is configured, else a template.

Only de-identified clinical values are sent to the API (no name or ID).
"""
import pandas as pd

from core.config import get_secret

# Check https://console.groq.com/docs/models for current model IDs (the catalog changes often).
DEFAULT_MODEL = "llama-3.3-70b-versatile"

SYSTEM = (
    "You are a clinical decision-support assistant writing a brief summary for a cardiologist. "
    "Use ONLY the data provided. Do not diagnose, prescribe or invent values; the final clinical "
    "decision remains with the doctor. Write about 150 words under these bold headings: "
    "Overview, Key risk drivers, Trends and alerts, Points for review."
)


def _context(patient: dict, score: float, category: str, factors: pd.DataFrame,
             vitals: pd.DataFrame, alerts: pd.DataFrame) -> str:
    lines = [f"Patient: {patient['age']}-year-old {'male' if patient['sex'] == 'M' else 'female'}.",
             f"Model risk score: {score:.0%} ({category} risk)."]
    lines.append("Top contributing factors: " + "; ".join(
        f"{r.label} ({'raises' if r.contribution > 0 else 'lowers'} risk)" for r in factors.head(5).itertuples()))
    if len(vitals) >= 2:
        last, base = vitals.iloc[-1], vitals.iloc[:-1].tail(5)
        lines.append(
            f"Latest vitals: BP {last.systolic_bp:.0f} mmHg (baseline {base.systolic_bp.mean():.0f}), "
            f"heart rate {last.heart_rate:.0f} bpm (baseline {base.heart_rate.mean():.0f}), "
            f"cholesterol {last.cholesterol:.0f} mg/dL (baseline {base.cholesterol.mean():.0f}).")
    open_alerts = alerts[~alerts["reviewed"]] if not alerts.empty else alerts
    if open_alerts.empty:
        lines.append("Open alerts: none.")
    else:
        lines.append("Open alerts: " + "; ".join(
            f"{a.severity} - {a.reason} ({a.alert_date:%d %b %Y})" for a in open_alerts.head(5).itertuples()))
    return "\n".join(lines)


def template_summary(context: str) -> str:
    return ("**Overview and data**\n\n" + context.replace("\n", "\n\n") +
            "\n\n**Points for review**\n\nReview the highest-weighted risk factors and any open alerts. "
            "This summary is generated from the model output and does not replace clinical judgement.")


def generate(patient, score, category, factors, vitals, alerts) -> tuple[str, str]:
    """Returns (summary_text, source) where source says which engine produced the text."""
    context = _context(patient, score, category, factors, vitals, alerts)
    key = get_secret("GROQ_API_KEY")
    if not key:
        return template_summary(context), "Template (no API key configured)"
    model = get_secret("GROQ_MODEL", DEFAULT_MODEL)
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=model, max_tokens=600, temperature=0.2,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": context}])
        return resp.choices[0].message.content, f"Groq ({model})"
    except Exception as exc:
        return template_summary(context), f"Template (API call failed: {type(exc).__name__})"
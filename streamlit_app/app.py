from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import streamlit as st


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


def api_base_url() -> str:
    return os.getenv("DATAOPS_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


def post_incident(payload: dict[str, Any], base_url: str | None = None) -> dict[str, Any]:
    url = f"{base_url or api_base_url()}/incidents/investigate"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach FastAPI backend at {url}") from exc


def build_payload(
    user_query: str,
    metric_name: str,
    dashboard_name: str,
    severity: str,
) -> dict[str, str]:
    return {
        "user_query": user_query,
        "metric_name": metric_name,
        "dashboard_name": dashboard_name,
        "severity": severity,
    }


def main() -> None:
    st.set_page_config(page_title="AI DataOps Incident Agent", layout="wide")
    st.title("AI DataOps Incident Agent")

    with st.sidebar:
        st.subheader("Backend")
        st.caption(api_base_url())

    with st.form("incident_form"):
        user_query = st.text_area(
            "Incident description",
            value="Revenue dropped by 40% in today's dashboard. Please investigate.",
            height=120,
        )
        col_a, col_b, col_c = st.columns([1, 1, 1])
        metric_name = col_a.text_input("Metric", value="revenue")
        dashboard_name = col_b.text_input("Dashboard", value="daily_revenue_dashboard")
        severity = col_c.selectbox("Severity", ["low", "medium", "high", "critical"], index=2)
        submitted = st.form_submit_button("Investigate")

    if not submitted:
        return

    payload = build_payload(user_query, metric_name, dashboard_name, severity)
    with st.spinner("Investigating incident..."):
        try:
            result = post_incident(payload)
        except RuntimeError as exc:
            st.error(str(exc))
            return

    response = result.get("response") or {}
    evidence = result.get("evidence") or []
    traces = result.get("traces") or []

    st.subheader("Investigation Result")
    st.write(response.get("likely_root_cause", "No response returned."))

    col_a, col_b, col_c = st.columns([1, 1, 1])
    col_a.metric("Incident Type", response.get("incident_type", "unknown"))
    col_b.metric("Confidence", response.get("confidence", "unknown"))
    approval = "Required" if response.get("requires_human_approval") else "Not required"
    col_c.metric("Human Approval", approval)

    st.subheader("Recommended Actions")
    for action in response.get("recommended_actions", []):
        st.write(f"- {action}")

    if response.get("requires_human_approval"):
        st.warning(response.get("escalation_reason", "Review required before taking action."))
        approve_col, escalate_col = st.columns([1, 1])
        approve_col.button("Approve")
        escalate_col.button("Escalate")

    st.subheader("Evidence")
    if evidence:
        st.dataframe(evidence, use_container_width=True)
    else:
        st.info("No evidence was collected.")

    st.subheader("Trace Timeline")
    if traces:
        st.dataframe(traces, use_container_width=True)
    else:
        st.info("No trace records were returned.")

    st.subheader("Evaluation Summary")
    st.info("Evaluation metrics will appear here after Phase 15.")


if __name__ == "__main__":
    main()

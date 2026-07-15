"""Streamlit dashboard for correlation discovery results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUTS = PROJECT_ROOT / "outputs"
PROCESSED = PROJECT_ROOT / "data" / "processed"
MERGED_PATH = OUTPUTS / "merged_county.csv"

REAL_PROCESSED = [
    "irs_990_county.csv",
    "census_acs_dp03_county.csv",
    "cdc_places_county.csv",
    "volunteer_county.csv",
]


@st.cache_data
def load_json(path: Path) -> dict | list | None:
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data
def load_merged() -> pd.DataFrame | None:
    if MERGED_PATH.exists():
        return pd.read_csv(MERGED_PATH)
    return None


def render_correlation_heatmap(matrix: dict | None) -> None:
    if not matrix:
        st.info("Run the pipeline to generate correlation heatmap data.")
        return
    df = pd.DataFrame(matrix)
    fig = px.imshow(
        df, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        title="Correlation Heatmap (Merged County Data)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_scatter(df: pd.DataFrame, x: str, y: str, color: str = "state_abbr") -> None:
    if x not in df.columns or y not in df.columns:
        st.warning(f"Columns not found: {x}, {y}")
        return
    fig = px.scatter(
        df, x=x, y=y, trendline="ols",
        color=color if color in df.columns else None,
        hover_data=["county_name"] if "county_name" in df.columns else None,
        title=f"{x.replace('_', ' ').title()} vs {y.replace('_', ' ').title()}",
    )
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="NORP Correlation Discovery", page_icon="📊", layout="wide")
    st.title("Agentic Data Exploration Layer")
    st.caption("Sociological Correlation Discovery in Nonprofit Datasets — CS6365")

    pipeline = load_json(OUTPUTS / "pipeline_results.json")
    correlations = load_json(OUTPUTS / "correlations.json")
    insights = load_json(OUTPUTS / "insights.json")
    validation = load_json(PROCESSED / "validation_report.json")
    merged = load_merged()

    config = pipeline.get("config", {}) if pipeline else {}
    state_label = config.get("states", "GA")

    tab_overview, tab_datasets, tab_correlations, tab_findings = st.tabs(
        ["Overview", "Datasets", "Correlations", "Findings"]
    )

    with tab_overview:
        st.subheader("Research Question")
        st.write(
            "What factors are most correlated with nonprofit success, funding growth, "
            "volunteer retention, and community impact?"
        )
        st.info(f"Current analysis scope: **{state_label}** counties")

        if pipeline:
            cols = st.columns(4)
            cols[0].metric("Discovery", pipeline.get("discovery", {}).get("message", "—"))
            cols[1].metric("Cleaning", pipeline.get("cleaning", {}).get("message", "—"))
            cols[2].metric("Validation", pipeline.get("validation", {}).get("message", "—"))
            cols[3].metric("Correlation", pipeline.get("correlation", {}).get("message", "—"))
        else:
            st.warning("Pipeline not yet run. Execute: `python run_pipeline.py`")

        if merged is not None:
            st.metric("Counties in merged analysis", len(merged))
            st.metric("Counties with nonprofits", int((merged.get("org_count", 0) > 0).sum()))

        st.subheader("Agent Workflow")
        st.code("Discovery → [Metabase] → Cleaning → Validation → Correlation → Insight → Dashboard")

    with tab_datasets:
        if validation and validation.get("reports"):
            st.subheader("Dataset Quality Scores")
            st.dataframe(pd.DataFrame(validation["reports"]), use_container_width=True)

            if validation.get("join_metrics"):
                st.subheader("Cross-Dataset Join Success")
                st.json(validation["join_metrics"])

        st.subheader(f"Processed Datasets ({state_label})")
        for name in REAL_PROCESSED:
            path = PROCESSED / name
            if path.exists():
                with st.expander(name):
                    st.dataframe(pd.read_csv(path), use_container_width=True)

        if merged is not None:
            st.subheader("Merged County Frame (used for correlations)")
            st.dataframe(merged, use_container_width=True)

    with tab_correlations:
        if correlations:
            mode = correlations.get("mode", "unknown")
            st.caption(f"Analysis mode: {mode} | Counties: {correlations.get('merged_counties', '—')}")

            top = correlations.get("top_correlations", [])[:10]
            if top:
                st.dataframe(pd.DataFrame(top), use_container_width=True)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[f"{r['variable_x']} ↔ {r['variable_y']}" for r in top],
                    y=[r["pearson_r"] for r in top],
                    marker_color=["#2ecc71" if r["pearson_r"] > 0 else "#e74c3c" for r in top],
                ))
                fig.update_layout(title="Top Significant Correlations", yaxis_title="Pearson r")
                st.plotly_chart(fig, use_container_width=True)

            render_correlation_heatmap(correlations.get("correlation_matrix"))

            st.subheader("Key Relationship Scatter Plots")
            if merged is not None:
                pairs = correlations.get("suggested_scatter_pairs", [
                    {"x": "median_household_income", "y": "total_volunteers"},
                    {"x": "unemployment_rate", "y": "volunteers_per_org"},
                    {"x": "median_household_income", "y": "org_count"},
                    {"x": "poverty_rate_all_people", "y": "total_revenue"},
                ])
                cols = st.columns(2)
                for i, pair in enumerate(pairs[:4]):
                    with cols[i % 2]:
                        render_scatter(merged, pair["x"], pair["y"])
            else:
                st.info("Run `python run_pipeline.py` to generate merged county data.")
        else:
            st.info("Run the pipeline to compute correlations.")

    with tab_findings:
        report_path = OUTPUTS / "research_report.md"
        if report_path.exists():
            st.markdown(report_path.read_text(encoding="utf-8"))
        elif insights:
            for i, finding in enumerate(insights.get("findings", []), 1):
                st.write(f"{i}. {finding}")

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            run_state = st.selectbox(
                "State scope",
                ["GA", "GA,FL", "GA,AL,SC", "ALL"],
                index=0,
            )
        with col_b:
            sync_mb = st.checkbox("Sync NORP Metabase first", value=False)

        if st.button("Run Pipeline"):
            with st.spinner("Running full agent pipeline..."):
                from run_pipeline import run_pipeline
                run_pipeline(
                    skip_insight_llm=True,
                    use_real_data=True,
                    state_filter=run_state,
                    sync_metabase=sync_mb,
                )
                st.success("Pipeline complete!")
                st.rerun()


if __name__ == "__main__":
    main()

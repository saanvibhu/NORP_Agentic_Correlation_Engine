# Project Plan — CS6365 Checkpoint 1

## Project Name

**Agentic Data Exploration Layer for Sociological Correlation Discovery in Nonprofit Datasets**

## Group

| Member | Responsibilities |
|--------|------------------|
| [Add Name 1] | Dataset research, ingestion, cleaning pipeline |
| [Add Name 2] | Architecture design, correlation engine, dashboard |

## Context and Related Work

The Non-Profit Organization Research Project (NORP) integrates nonprofit data from the IRS, Census, and socioeconomic indicators to support data-driven research on volunteer engagement, funding, education, healthcare, and community impact.

Previous NORP work explored Natural Language-to-SQL (NL2SQL) using LLMs. While query execution worked well, these approaches failed at **knowledge discovery** — generating SQL does not directly surface meaningful sociological insights. Prior research also demonstrated the importance of automating data integration, cleaning, and preparation across heterogeneous datasets.

This project addresses that gap with a multi-agent system that autonomously discovers correlations rather than requiring researchers to ask the right questions first.

## Project Deliverables

| Deliverable | Description | Stack | Status |
|-------------|-------------|-------|--------|
| Dataset Discovery Agent | Identifies and imports datasets from NORP and external sources | Python, Pandas, APIs | ✅ Checkpoint 1 |
| Data Cleaning Agent | Standardizes schemas, handles nulls, removes duplicates | Python, Pandas | ✅ Checkpoint 1 |
| Data Validation Agent | Quality scoring, join rates, completeness | Python, Pandas | ✅ Checkpoint 1 |
| Correlation Analysis Engine | Pearson, Spearman, MI, regression | Scikit-learn, Statsmodels | ✅ Checkpoint 1 |
| Insight Generation Agent | Human-readable findings from statistics | OpenAI/Claude API | ✅ Checkpoint 1 |
| Interactive Dashboard | Visualizations and findings display | Streamlit, Plotly | ✅ Checkpoint 1 |
| Final Research Report | Sociological correlation summary | Markdown, PDF | 🔲 Checkpoint 3 |

## Milestones

### Checkpoint 1 — Project Planning & Architecture (Current)

**Scope:**
- Define project objectives and research question
- Design multi-agent architecture
- Identify initial datasets
- Create GitHub repository
- Implement agent skeletons with sample data pipeline

**Status:** ✅ Completed

### Checkpoint 2 — Data Discovery & Cleaning Pipeline

**Scope:**
- Implement live dataset ingestion from NORP Metabase
- Integrate 3+ external datasets (Census, BLS, Data.gov)
- Expand cleaning rules for real-world schema variations
- Build automated ingestion workflow

**Status:** 🔲 Planned

### Checkpoint 3 — Analysis Engine & Insight Generation

**Scope:**
- Full validation with Great Expectations
- LangGraph agent orchestration
- Dashboard visualizations (heatmaps, scatter, network graphs)
- Evaluation, testing, final research report

**Status:** 🔲 Planned

## Current Progress Report

### Work Completed (Last Two Weeks)

- Brainstormed project concepts aligned with professor's NORP vision
- Selected Agentic Data Exploration Layer approach
- Researched data sources: NORP, Data.gov, Census, BLS, Kaggle, IRS 990
- Designed multi-agent architecture (see `docs/architecture.md`)
- Created repository with working agent pipeline
- Built sample datasets demonstrating correlation discovery
- Implemented Streamlit dashboard

### Comparison Against Planned Milestone

Project is aligned with Checkpoint 1 objectives. All planned deliverables for this checkpoint are implemented with sample data.

### Planned Work (Next Two Weeks)

- Acquire real datasets from NORP Metabase and Data.gov
- Expand Discovery Agent with API-based download
- Test cleaning agent on heterogeneous schemas
- Establish Great Expectations validation suite
- Integrate at least three live datasets

### Changes to Original Plan

No major scope changes. Sample data used for Checkpoint 1 demo; live ingestion deferred to Checkpoint 2 as planned.

## Dataset Source Inventory

| Source | Data Type | Join Key | Priority |
|--------|-----------|----------|----------|
| NORP Metabase | Nonprofit org metrics | organization_id | High |
| IRS Form 990 | Revenue, expenses | EIN | High |
| U.S. Census ACS | Demographics, income | zip_code, county | High |
| Bureau of Labor Statistics | Unemployment | county FIPS | Medium |
| Data.gov | Volunteer programs | state, zip | Medium |
| Kaggle Nonprofit Datasets | Various | varies | Low |

## Self-Evaluation

| Criterion | Score | Notes |
|-----------|-------|-------|
| Plan | 95 | Clear scope, architecture, measurable deliverables |
| Match | 95 | Progress aligns with Checkpoint 1 milestone |
| Factual | 95 | Repository artifacts support reported progress |

## Skill Learning Report

- **Agentic AI:** Multi-agent coordination for specialized data tasks
- **Data Engineering:** Ingestion, transformation, normalization, quality assessment
- **Statistical Analysis:** Correlation, hypothesis testing, significance evaluation
- **Enterprise Integration:** Combining heterogeneous datasets into unified pipeline
- **Dashboard Development:** Streamlit and Plotly visualization

# NORP_Agentic_Correlation_Engine



## Overview

This project is for CS 6365: Introduction to Enterprise Computing.

The goal of this project is to build an Agentic Data Exploration Layer that can automatically discover, clean, validate, and analyze nonprofit datasets. Instead of requiring researchers to manually work through large amounts of data, the system will help identify correlations and trends across datasets.

## Problem Statement

Nonprofit datasets often come from different sources and are difficult to combine and analyze. Researchers spend a lot of time cleaning data before they can begin looking for patterns and relationships.

The goal of this project is to make that process faster by automating data discovery, cleaning, validation, and analysis.

## Research Question

What sociological, demographic, and economic factors are most strongly related to nonprofit outcomes such as volunteer engagement, funding growth, and community impact?

## Proposed Architecture

The project will use multiple agents that each have a specific responsibility.

### Dataset Discovery Agent
- Finds and imports datasets from various sources

### Data Cleaning Agent
- Standardizes data formats
- Handles missing values
- Removes duplicates

### Data Validation Agent
- Evaluates data quality
- Measures completeness and consistency

### Correlation Analysis Agent
- Computes statistical relationships between variables
- Identifies significant correlations

### Insight Generation Agent
- Generates human-readable explanations of findings
- Summarizes discovered trends and patterns

Together, these agents will help researchers move from raw data to meaningful insights more efficiently.

## Data Sources

Potential datasets include:

- NORP datasets
- IRS nonprofit data
- U.S. Census Bureau data
- Data.gov datasets
- Bureau of Labor Statistics datasets
- Kaggle datasets

## Technology Stack

- Python
- Pandas
- NumPy
- Scikit-Learn
- Statsmodels
- LangGraph
- Streamlit
- Plotly

## Project Status

We are currently in the planning phase of the project.

So far, we have:

The next step is to begin collecting datasets and implementing the agent pipeline.
 project.

## Implemented Pipeline

The execution order is `Discovery -> Cleaning -> Deterministic Validation Gate -> Correlation -> Ranking -> Insight -> Report`.

The Verifier/Critic gate evaluates row counts, duplicate rates, missingness, numeric columns, and join success before correlation analysis. Rejected datasets include failure reasons and recommended corrective actions in `data/processed/validation_report.json`.

Correlation analysis computes Pearson and Spearman coefficients, p-values, sample sizes, and optional Pearson confidence intervals. A finding is marked significant only when configured sample-size, p-value, and magnitude thresholds pass. Ranked findings are saved to `outputs/ranked_correlations.json`.

## Configuration and Commands

Thresholds live in `config.yaml`; `agents/config.py` uses safe defaults if it is missing or malformed.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py --sample
pytest
streamlit run dashboard/app.py
```

Real-data execution is `python run_pipeline.py`, with optional `--state GA,FL`, `--with-llm`, and `--no-fetch-volunteer` flags. Expected outputs include `data/processed/validation_report.json`, `outputs/correlations.json`, `outputs/ranked_correlations.json`, `outputs/insights.json`, `outputs/research_report.md`, and `outputs/merged_county.csv` when a merge is available. Pipeline events are written to `logs/pipeline.log`.
## Team Members

- Saanvi Bhumpalle
- Tanya Kharuna
- Zaara Syeda

## Repository

This repository contains the code, documentation, and resources for our CS 6365 project.

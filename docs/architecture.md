 # Pipeline Architecture

The ordered workflow is `Discovery -> Cleaning -> Validation -> Correlation -> Ranking -> Insight -> Report`.

The deterministic Verifier/Critic validates row counts, duplicate rates, missing values, numeric columns, and join success. It is a hard gate: only accepted dataset filenames are passed to correlation analysis, and rejected datasets receive failure reasons and corrective actions in `data/processed/validation_report.json`.

Correlation analysis computes Pearson and Spearman coefficients, p-values, sample sizes, regression details, and optional Pearson confidence intervals. Significance requires the configured minimum sample size, p-value threshold, and correlation magnitude. Ranking consumes only significant approved findings and scores strength, statistical evidence, sample size, quality, and missingness.

`agents/config.py` loads `config.yaml` and falls back to safe defaults when configuration is missing or malformed. Shared logging writes timestamped pipeline events to `logs/pipeline.log`. Insight generation reads ranked deterministic output and includes evidence, confidence, limitations, and the reminder that correlation does not imply causation.

Install with `pip install -r requirements.txt`, run `python run_pipeline.py --sample`, run `pytest`, and launch the dashboard with `streamlit run dashboard/app.py`. Outputs include validation, correlation, ranked-correlation, insight, merged-data, and research-report files under `data/processed/` and `outputs/`.


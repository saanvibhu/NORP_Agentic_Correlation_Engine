# Sociological Correlation Discovery Report

## Project Overview
This report summarizes statistically evaluated relationships discovered by the sample-data correlation pipeline.

## Research Question
What factors are most correlated with nonprofit success, funding growth, volunteer retention, and community impact?

## Key Findings

## Datasets Used
Validated datasets supplied by the deterministic pipeline gate.

## Top Ranked Correlations
1. volunteer_hours vs engagement_score: r=0.7985, p=2e-06, n=25
2. volunteer_hours vs retention_rate: r=0.7937, p=2e-06, n=25
3. volunteer_hours vs education_pct: r=0.6588, p=0.000342, n=25
4. volunteer_hours vs median_income: r=0.6460, p=0.000486, n=25
5. volunteer_hours vs unemployment_rate: r=-0.5911, p=0.001862, n=25
6. median_income vs education_pct: r=0.9985, p=0.0, n=25
7. retention_rate vs engagement_score: r=0.9969, p=0.0, n=25
8. funding vs volunteer_hours: r=0.9961, p=0.0, n=25
9. funding vs revenue: r=0.9955, p=0.0, n=25
10. revenue vs volunteer_hours: r=0.9912, p=0.0, n=25
11. median_income vs unemployment_rate: r=-0.9750, p=0.0, n=25
12. education_pct vs unemployment_rate: r=-0.9747, p=0.0, n=25
13. unemployment_rate vs population: r=0.9734, p=0.0, n=25
14. retention_rate vs education_pct: r=0.9589, p=0.0, n=25
15. retention_rate vs median_income: r=0.9546, p=0.0, n=25

## Generated Interpretations
1. Volunteer Hours is positively associated with Engagement Score. Volunteer Hours is strongly positively correlated with Engagement Score (r = 0.80, p = 0.0000).
   Evidence: Correlation coefficient = 0.7985; p-value = 2e-06; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
2. Volunteer Hours is positively associated with Retention Rate. Volunteer engagement tends to correlate with local retention outcomes. Observed correlation: r = 0.79 (~79% explained variance).
   Evidence: Correlation coefficient = 0.7937; p-value = 2e-06; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
3. Volunteer Hours is positively associated with Education Pct. Volunteer Hours is moderately positively correlated with Education Pct (r = 0.66, p = 0.0003).
   Evidence: Correlation coefficient = 0.6588; p-value = 0.000342; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
4. Volunteer Hours is positively associated with Median Income. Volunteer participation correlates with local median income levels. Observed correlation: r = 0.65 (~65% explained variance).
   Evidence: Correlation coefficient = 0.6460; p-value = 0.000486; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
5. Volunteer Hours is negatively associated with Unemployment Rate. Volunteer engagement tends to decrease in areas with higher unemployment. Observed correlation: r = -0.59 (~59% explained variance).
   Evidence: Correlation coefficient = -0.5911; p-value = 0.001862; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
6. Median Income is positively associated with Education Pct. Median Income is strongly positively correlated with Education Pct (r = 1.00, p = 1.0000).
   Evidence: Correlation coefficient = 0.9985; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
7. Retention Rate is positively associated with Engagement Score. Retention Rate is strongly positively correlated with Engagement Score (r = 1.00, p = 1.0000).
   Evidence: Correlation coefficient = 0.9969; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
8. Funding is positively associated with Volunteer Hours. Funding is strongly positively correlated with Volunteer Hours (r = 1.00, p = 1.0000).
   Evidence: Correlation coefficient = 0.9961; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
9. Funding is positively associated with Revenue. Funding is strongly positively correlated with Revenue (r = 1.00, p = 1.0000).
   Evidence: Correlation coefficient = 0.9955; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
10. Revenue is positively associated with Volunteer Hours. Revenue is strongly positively correlated with Volunteer Hours (r = 0.99, p = 1.0000).
   Evidence: Correlation coefficient = 0.9912; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
11. Median Income is negatively associated with Unemployment Rate. Median Income is strongly negatively correlated with Unemployment Rate (r = -0.97, p = 1.0000).
   Evidence: Correlation coefficient = -0.9750; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
12. Education Pct is negatively associated with Unemployment Rate. Education Pct is strongly negatively correlated with Unemployment Rate (r = -0.97, p = 1.0000).
   Evidence: Correlation coefficient = -0.9747; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
13. Unemployment Rate is positively associated with Population. Unemployment Rate is strongly positively correlated with Population (r = 0.97, p = 1.0000).
   Evidence: Correlation coefficient = 0.9734; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
14. Retention Rate is positively associated with Education Pct. Higher educational attainment is associated with improved volunteer retention. Observed correlation: r = 0.96 (~96% explained variance).
   Evidence: Correlation coefficient = 0.9589; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.
15. Retention Rate is positively associated with Median Income. Retention Rate is strongly positively correlated with Median Income (r = 0.95, p = 1.0000).
   Evidence: Correlation coefficient = 0.9546; p-value = 0.0; sample size = 25. Confidence: moderate.
   Limitation: The result is observational and may be affected by confounding variables, measurement choices, and missing data. Correlation does not imply causation.

## Generated Hypotheses
- Does median household income affect educational attainment?
- Does median household income affect local unemployment rate?
- Does median household income affect population density?
- Does median household income affect volunteer engagement?
- Does median household income affect volunteer retention?
- Does educational attainment affect local unemployment rate?
- Does educational attainment affect population density?
- Does educational attainment affect volunteer engagement?
- Does educational attainment affect volunteer retention?
- Does local unemployment rate affect population density?
- Does local unemployment rate affect volunteer engagement?
- Does local unemployment rate affect volunteer retention?
- Does population density affect volunteer engagement?
- Does population density affect volunteer retention?
- Does volunteer engagement affect volunteer retention?

## Validation Summary
Only datasets accepted by the deterministic validation gate were used.

## Limitations
Results are based on sample data and observational correlations. Missing variables, confounding factors, and small sample sizes may affect interpretation.

## Future Improvements
Add real IRS, Census, and CDC ingestion, stronger multiple-testing controls, and longitudinal causal analysis.
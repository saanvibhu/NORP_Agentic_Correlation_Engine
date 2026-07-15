"""Agent 5: Insight Generation — converts statistics into research findings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agents.base import OUTPUTS_DIR, AgentResult, save_json, setup_logger
from agents.correlation_agent import CorrelationResult

logger = setup_logger(__name__)


class InsightAgent:
    """Generates human-readable findings from correlation results."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and (
            bool(os.getenv("OPENAI_API_KEY")) or bool(os.getenv("ANTHROPIC_API_KEY"))
        )

    @staticmethod
    def _template_insight(result: dict) -> str:
        x, y = result["variable_x"], result["variable_y"]
        r = result["pearson_r"]
        direction = "positively" if r > 0 else "negatively"
        strength = "strongly" if abs(r) >= 0.7 else "moderately" if abs(r) >= 0.5 else "weakly"
        return (
            f"{x.replace('_', ' ').title()} is {strength} {direction} correlated "
            f"with {y.replace('_', ' ').title()} (r = {r:.2f}, p = {result['pearson_p']:.4f})."
        )

    @staticmethod
    def _sociological_framing(result: dict) -> str:
        """Add nonprofit/sociological context to statistical findings."""
        x = result["variable_x"].lower()
        y = result["variable_y"].lower()
        r = result["pearson_r"]

        templates = [
            ("volunteer", "unemployment", "Volunteer engagement tends to decrease in areas with higher unemployment"),
            ("volunteer", "retention", "Volunteer engagement tends to correlate with local retention outcomes"),
            ("volunteer", "income", "Volunteer participation correlates with local median income levels"),
            ("total_volunteers", "median_household_income", "Counties with more nonprofit volunteers show distinct income profiles"),
            ("volunteers_per_org", "education", "Volunteers per organization relate to local educational attainment"),
            ("retention", "education", "Higher educational attainment is associated with improved volunteer retention"),
            ("funding", "income", "Nonprofit funding growth correlates with local median income levels"),
            ("donation", "population", "Donation volumes scale with population density in served communities"),
        ]

        for key_x, key_y, narrative in templates:
            if (key_x in x and key_y in y) or (key_y in x and key_x in y):
                pct = abs(r) * 100
                return f"{narrative}. Observed correlation: r = {r:.2f} (~{pct:.0f}% explained variance)."

        return InsightAgent._template_insight(result)

    def generate_hypotheses(self, column_names: list[str]) -> list[str]:
        """Generate candidate research hypotheses (Project Idea 5)."""
        keywords = {
            "income": "median household income",
            "education": "educational attainment",
            "unemployment": "local unemployment rate",
            "population": "population density",
            "volunteer": "volunteer engagement",
            "volunteers": "volunteer participation",
            "retention": "volunteer retention",
        }
        present = {k: v for k, v in keywords.items() if any(k in c.lower() for c in column_names)}
        hypotheses = []
        items = list(present.items())
        for i, (k1, label1) in enumerate(items):
            for k2, label2 in items[i + 1 :]:
                hypotheses.append(f"Does {label1} affect {label2}?")
        return hypotheses[:20]

    def _llm_enhance(self, findings: list[str]) -> str | None:
        if not self.use_llm:
            return None
        try:
            if os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI

                client = OpenAI()
                prompt = (
                    "You are a sociological research assistant analyzing nonprofit data. "
                    "Synthesize these statistical findings into 2-3 paragraph research summary "
                    "with actionable implications for nonprofit leaders:\n\n"
                    + "\n".join(f"- {f}" for f in findings[:10])
                )
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600,
                )
                return response.choices[0].message.content
            if os.getenv("ANTHROPIC_API_KEY"):
                import anthropic

                client = anthropic.Anthropic()
                prompt = (
                    "Synthesize these nonprofit correlation findings into a brief research summary:\n\n"
                    + "\n".join(f"- {f}" for f in findings[:10])
                )
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=600,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text
        except Exception as exc:
            logger.warning("LLM enhancement unavailable: %s", exc)
        return None

    def run(self, correlations_path: Path | None = None) -> AgentResult:
        path = correlations_path or (OUTPUTS_DIR / "correlations.json")
        if not path.exists():
            return AgentResult(
                agent="insight",
                success=False,
                message=f"Correlations file not found: {path}",
            )

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        top = data.get("top_correlations", data.get("all_correlations", []))[:15]
        seen: set[tuple[str, str]] = set()
        findings: list[str] = []
        for r in top:
            key = tuple(sorted((r["variable_x"], r["variable_y"])))
            if key in seen:
                continue
            seen.add(key)
            findings.append(self._sociological_framing(r))

        columns = set()
        for r in top:
            columns.add(r["variable_x"])
            columns.add(r["variable_y"])
        hypotheses = self.generate_hypotheses(list(columns))

        llm_summary = self._llm_enhance(findings)

        report = {
            "research_question": (
                "What factors are most correlated with nonprofit success, funding growth, "
                "volunteer retention, and community impact?"
            ),
            "findings": findings,
            "hypotheses_generated": hypotheses,
            "llm_summary": llm_summary,
            "finding_count": len(findings),
        }

        md_lines = [
            "# Sociological Correlation Discovery Report",
            "",
            "## Research Question",
            report["research_question"],
            "",
            "## Key Findings",
        ]
        for i, finding in enumerate(findings, 1):
            md_lines.append(f"{i}. {finding}")

        if hypotheses:
            md_lines.extend(["", "## Generated Hypotheses"])
            for h in hypotheses:
                md_lines.append(f"- {h}")

        if llm_summary:
            md_lines.extend(["", "## AI Research Summary", llm_summary])

        report_path = OUTPUTS_DIR / "research_report.md"
        report_path.write_text("\n".join(md_lines), encoding="utf-8")
        save_json(report, OUTPUTS_DIR / "insights.json")

        return AgentResult(
            agent="insight",
            success=True,
            message=f"Generated {len(findings)} findings and {len(hypotheses)} hypotheses",
            data=report,
        )


if __name__ == "__main__":
    result = InsightAgent(use_llm=False).run()
    print(result.message)

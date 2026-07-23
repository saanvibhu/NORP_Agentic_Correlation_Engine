#!/usr/bin/env python3
"""End-to-end multi-agent pipeline orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.base import OUTPUTS_DIR, save_json, setup_logger
from agents.cleaning_agent import CleaningAgent
from agents.correlation_agent import CorrelationAgent
from agents.config import load_config
from agents.dataset_registry import SAMPLE_DATASETS, active_real_specs
from agents.discovery_agent import DiscoveryAgent
from agents.insight_agent import InsightAgent
from agents.ranking_agent import RankingAgent
from agents.metabase_client import sync_norp_datasets
from agents.state_utils import parse_state_filter, state_label
from agents.validation_agent import ValidationAgent
from agents.volunteer_fetcher import ensure_volunteer_raw

logger = setup_logger("pipeline")


def run_pipeline(
    skip_insight_llm: bool = True,
    use_real_data: bool = True,
    state_filter: str = "GA",
    sync_metabase: bool = False,
    fetch_volunteer: bool = True,
) -> dict:
    """Execute: discover → [metabase] → clean → validate → correlate → insight."""
    config = load_config()
    logger.info("Pipeline start")
    results: dict = {}
    states = parse_state_filter(state_filter) if use_real_data else None
    catalog = active_real_specs(states) if use_real_data else SAMPLE_DATASETS

    if sync_metabase and use_real_data:
        logger.info("=== NORP Metabase Sync ===")
        mb = sync_norp_datasets()
        results["metabase"] = mb.to_dict()

    if fetch_volunteer and use_real_data:
        logger.info("=== Volunteer Data (Census CPS) ===")
        path = ensure_volunteer_raw(states)
        results["volunteer_fetch"] = {
            "success": path is not None,
            "message": f"CPS volunteer data at {path}" if path else "CPS fetch skipped — using IRS volunteer fields",
        }

    logger.info("=== Agent 1: Dataset Discovery ===")
    discovery = DiscoveryAgent(use_real_data=use_real_data).run()
    results["discovery"] = discovery.to_dict()
    if not discovery.success:
        return results

    accepted_specs = [
        spec for spec in catalog
        if any(a["name"] == spec.name for a in discovery.data.get("accepted", []))
    ]
    # Always include volunteer if IRS accepted (uses IRS volunteer metrics)
    if use_real_data and any(s.name == "irs_990" for s in accepted_specs):
        vol_spec = next((s for s in catalog if s.name == "volunteer_cps"), None)
        if vol_spec and vol_spec not in accepted_specs:
            accepted_specs.append(vol_spec)

    processed_names = [s.processed_name for s in accepted_specs]
    logger.info("States: %s | Datasets: %s", state_label(states), [s.name for s in accepted_specs])

    logger.info("=== Agent 2: Data Cleaning ===")
    cleaning = CleaningAgent(
        use_real_data=use_real_data,
        state_filter=state_filter,
    ).run(
        specs=accepted_specs if use_real_data else None,
        filenames=None if use_real_data else processed_names,
    )
    results["cleaning"] = cleaning.to_dict()

    logger.info("=== Agent 3: Verification ===")
    validation = ValidationAgent(use_real_data=use_real_data, config=config).run(filenames=processed_names)
    results["validation"] = validation.to_dict()

    validated = validation.data.get("accepted", processed_names)
    if not validated:
        return results

    logger.info("=== Agent 4: Correlation Analysis ===")
    correlation = CorrelationAgent(use_real_data=use_real_data, states=states, config=config).run(filenames=validated)
    results["correlation"] = correlation.to_dict()

    logger.info("Correlation counts: total=%s significant=%s", correlation.data.get("total_pairs_analyzed", 0) if correlation.data else 0, correlation.data.get("significant_findings", 0) if correlation.data else 0)
    logger.info("=== Agent 5: Correlation Ranking ===")
    ranking = RankingAgent(config=config).run()
    results["ranking"] = ranking.to_dict()

    logger.info("=== Agent 6: Insight Generation ===")
    insight = InsightAgent(use_llm=not skip_insight_llm).run()
    results["insight"] = insight.to_dict()

    save_json(
        {**results, "config": {**config.to_dict(), "states": state_label(states), "use_real_data": use_real_data}},
        OUTPUTS_DIR / "pipeline_results.json",
    )
    logger.info("Pipeline complete. Outputs: %s", OUTPUTS_DIR)
    logger.info("Pipeline finish")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="NORP Agentic Correlation Discovery Engine")
    parser.add_argument("--with-llm", action="store_true", help="Enable LLM insight generation")
    parser.add_argument("--sample", action="store_true", help="Use sample demo datasets")
    parser.add_argument(
        "--state",
        default="GA",
        help="State filter: GA, GA,FL,TX or ALL (default: GA)",
    )
    parser.add_argument("--sync-metabase", action="store_true", help="Pull NORP tables from Metabase")
    parser.add_argument("--no-fetch-volunteer", action="store_true", help="Skip Census CPS volunteer fetch")
    args = parser.parse_args()

    results = run_pipeline(
        skip_insight_llm=not args.with_llm,
        use_real_data=not args.sample,
        state_filter=args.state,
        sync_metabase=args.sync_metabase,
        fetch_volunteer=not args.no_fetch_volunteer,
    )
    print(json.dumps({k: v.get("message", str(v)) for k, v in results.items() if isinstance(v, dict)}, indent=2))


if __name__ == "__main__":
    main()

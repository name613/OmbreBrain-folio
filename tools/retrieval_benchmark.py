#!/usr/bin/env python3
"""Run a deterministic, synthetic Ombre Brain retrieval benchmark."""

from __future__ import annotations

import argparse
import atexit
import asyncio
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bucket_manager import BucketManager


DEFAULT_CASES = ROOT / "benchmarks" / "retrieval_cases.json"
DEFAULT_LIMIT = 5


def load_cases(path: Path = DEFAULT_CASES) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("unsupported benchmark version")
    bucket_ids = {
        str(bucket.get("fixture_id", "")).strip()
        for bucket in data.get("buckets", [])
    }
    if "" in bucket_ids or len(bucket_ids) != len(data.get("buckets", [])):
        raise ValueError("bucket fixture_id values must be unique and non-empty")
    for query in data.get("queries", []):
        relevant = set(query.get("relevant", []))
        if not relevant <= bucket_ids:
            raise ValueError("query references an unknown fixture_id")
    for bucket in data.get("buckets", []):
        age_days = bucket.get("age_days", 0)
        if not isinstance(age_days, (int, float)) or age_days < 0:
            raise ValueError("bucket age_days must be a non-negative number")
    return data


def benchmark_config(base_dir: str, scoring: dict[str, Any]) -> dict[str, Any]:
    return {
        "buckets_dir": base_dir,
        "matching": {"fuzzy_threshold": 50, "max_results": DEFAULT_LIMIT},
        "wikilink": {"enabled": False},
        "scoring_weights": {
            "topic_relevance": 4.0,
            "emotion_resonance": 2.0,
            "time_proximity": 2.5,
            "importance": 1.0,
            "content_weight": 3.0,
            **scoring,
        },
    }


def summarize_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    judged = [row for row in rows if row["relevant"]]
    expected_empty = [row for row in rows if not row["relevant"]]
    reciprocal_ranks = []
    field_counts: Counter[str] = Counter()
    strategy_counts: Counter[str] = Counter()
    group_top1: dict[str, list[str | None]] = defaultdict(list)

    for row in judged:
        ranked = row["ranked_fixture_ids"]
        relevant = set(row["relevant"])
        rank = next(
            (index for index, fixture_id in enumerate(ranked, start=1)
             if fixture_id in relevant),
            None,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        if rank:
            hit = row["results"][rank - 1]
            field_counts.update(hit.get("matched_in", []))
            strategy_counts.update([hit.get("retrieval_strategy", "fuzzy")])
        group_top1[row["intent_group"]].append(ranked[0] if ranked else None)

    stable_groups = [
        values
        for values in group_top1.values()
        if len(values) >= 2
    ]
    top1_stability = (
        sum(None not in values and len(set(values)) == 1 for values in stable_groups)
        / len(stable_groups)
        if stable_groups
        else 1.0
    )

    def hit_at(k: int) -> float:
        if not judged:
            return 0.0
        return sum(
            bool(set(row["ranked_fixture_ids"][:k]) & set(row["relevant"]))
            for row in judged
        ) / len(judged)

    return {
        "query_count": len(rows),
        "judged_query_count": len(judged),
        "hit_at_1": round(hit_at(1), 4),
        "hit_at_5": round(hit_at(5), 4),
        "mrr": round(sum(reciprocal_ranks) / len(judged), 4) if judged else 0.0,
        "top1_noise_rate": round(1 - hit_at(1), 4) if judged else 0.0,
        "no_result_rate": round(
            sum(not row["ranked_fixture_ids"] for row in rows) / len(rows),
            4,
        ) if rows else 0.0,
        "expected_empty_accuracy": round(
            sum(not row["ranked_fixture_ids"] for row in expected_empty)
            / len(expected_empty),
            4,
        ) if expected_empty else 1.0,
        "top1_stability": round(top1_stability, 4),
        "relevant_hit_fields": dict(sorted(field_counts.items())),
        "relevant_hit_strategies": dict(sorted(strategy_counts.items())),
    }


async def evaluate_profile(
    cases: dict[str, Any],
    scoring: dict[str, Any],
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ombre-retrieval-benchmark-") as temp_dir:
        for directory in ("permanent", "dynamic", "archive", "feel"):
            os.makedirs(os.path.join(temp_dir, directory), exist_ok=True)
        manager = BucketManager(benchmark_config(temp_dir, scoring))
        actual_to_fixture: dict[str, str] = {}

        try:
            for bucket in cases["buckets"]:
                payload = {
                    key: value
                    for key, value in bucket.items()
                    if key not in {"fixture_id", "age_days"}
                }
                actual_id = await manager.create(**payload)
                actual_to_fixture[actual_id] = bucket["fixture_id"]
                age_days = float(bucket.get("age_days", 0))
                if age_days:
                    bucket_path = manager._find_bucket_file(actual_id)
                    post = frontmatter.load(bucket_path)
                    timestamp = (
                        datetime.now() - timedelta(days=age_days)
                    ).isoformat(timespec="seconds")
                    post["created"] = timestamp
                    post["last_active"] = timestamp
                    Path(bucket_path).write_text(
                        frontmatter.dumps(post),
                        encoding="utf-8",
                    )

            rows = []
            for query in cases["queries"]:
                results = await manager.search(
                    query["query"],
                    limit=limit,
                    record_stats=False,
                )
                summarized = []
                for result in results:
                    fixture_id = actual_to_fixture.get(result.get("id"))
                    if not fixture_id:
                        continue
                    summarized.append({
                        "fixture_id": fixture_id,
                        "score": result.get("score"),
                        "matched_in": result.get("matched_in", []),
                        "field_scores": result.get("field_scores", {}),
                        "retrieval_strategy": result.get(
                            "retrieval_strategy",
                            "fuzzy",
                        ),
                        "tokens_hit": result.get("tokens_hit", {}),
                        "token_coverage": result.get("token_coverage", 0.0),
                    })
                rows.append({
                    "query_id": query["query_id"],
                    "intent_group": query["intent_group"],
                    "query": query["query"],
                    "relevant": query["relevant"],
                    "ranked_fixture_ids": [
                        result["fixture_id"] for result in summarized
                    ],
                    "results": summarized,
                })
        finally:
            # BucketManager registers a forced atexit flush. This benchmark
            # deliberately deletes its temporary store before process exit,
            # so unregister that one callback instead of logging a false
            # persistence error after a successful run.
            atexit.unregister(manager._flush_hit_stats)

    return {
        "scoring": scoring,
        "metrics": summarize_metrics(rows),
        "queries": rows,
    }


async def run(path: Path) -> dict[str, Any]:
    cases = load_cases(path)
    baseline = await evaluate_profile(cases, {})
    candidate = await evaluate_profile(cases, {
        "multi_token_fallback": True,
        "multi_token_min_coverage": 0.4,
        "procedure_intent_boost": 1.08,
    })
    return {
        "benchmark_version": cases["version"],
        "source": "synthetic",
        "baseline": baseline,
        "candidate": candidate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(run(args.cases))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

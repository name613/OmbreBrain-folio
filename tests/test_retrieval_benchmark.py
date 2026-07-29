import pytest

from tools.retrieval_benchmark import (
    evaluate_profile,
    load_cases,
    summarize_metrics,
)


def test_benchmark_schema_rejects_unknown_relevant_id(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(
        """
        {
          "version": 1,
          "buckets": [{"fixture_id": "known"}],
          "queries": [{"relevant": ["missing"]}]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown fixture_id"):
        load_cases(path)


def test_metric_summary_counts_fields_and_expected_empty():
    rows = [
        {
            "intent_group": "one",
            "relevant": ["target"],
            "ranked_fixture_ids": ["target", "noise"],
            "results": [{
                "fixture_id": "target",
                "matched_in": ["subject", "content"],
                "retrieval_strategy": "multi_token_fallback",
            }],
        },
        {
            "intent_group": "empty",
            "relevant": [],
            "ranked_fixture_ids": [],
            "results": [],
        },
    ]

    metrics = summarize_metrics(rows)

    assert metrics["hit_at_1"] == 1.0
    assert metrics["expected_empty_accuracy"] == 1.0
    assert metrics["relevant_hit_fields"] == {"content": 1, "subject": 1}
    assert metrics["relevant_hit_strategies"] == {"multi_token_fallback": 1}


@pytest.mark.asyncio
async def test_candidate_profile_is_not_worse_than_baseline():
    cases = load_cases()
    baseline = await evaluate_profile(cases, {})
    candidate = await evaluate_profile(cases, {
        "multi_token_fallback": True,
        "multi_token_min_coverage": 0.4,
        "procedure_intent_boost": 1.08,
    })

    assert candidate["metrics"]["hit_at_5"] >= baseline["metrics"]["hit_at_5"]
    assert candidate["metrics"]["mrr"] >= baseline["metrics"]["mrr"]
    assert candidate["metrics"]["expected_empty_accuracy"] == 1.0
    assert (
        candidate["metrics"]["relevant_hit_strategies"]
        .get("multi_token_fallback", 0)
        >= 1
    )
    assert (
        candidate["metrics"]["hit_at_1"]
        > baseline["metrics"]["hit_at_1"]
    )

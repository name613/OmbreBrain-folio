import pytest


def test_single_short_tag_does_not_fully_match_long_question(bucket_mgr):
    score = bucket_mgr._calc_list_field_match(
        "睡晚了要怎么计算惩罚",
        ["惩罚", "情感"],
    )

    assert 0 < score < bucket_mgr._MATCH_THRESHOLD


def test_multiple_specific_tags_cover_a_natural_question(bucket_mgr):
    score = bucket_mgr._calc_list_field_match(
        "暖溪村 API 种地",
        ["暖溪村", "API", "种地"],
    )

    assert score == pytest.approx(100.0)


def test_short_exact_tag_query_still_scores_fully(bucket_mgr):
    score = bucket_mgr._calc_list_field_match("还账", ["还账", "规则"])

    assert score == pytest.approx(100.0)


def test_attached_request_verb_keeps_entity_token(bucket_mgr):
    tokens = bucket_mgr._split_query_tokens("查蓝塔凭证以及月门操作")

    assert "蓝塔" in tokens
    assert "以及" not in tokens


@pytest.mark.asyncio
async def test_generic_domain_no_longer_outranks_specific_procedure(bucket_mgr):
    activity_id = await bucket_mgr.create(
        content="参加丰收节并完成农场任务。",
        name="丰收节活动记录",
        domain=["游戏"],
        tags=["农场", "活动"],
        importance=8,
    )
    procedure_id = await bucket_mgr.create(
        content="先购买种子，再选择地块种下。",
        name="暖溪村种地步骤",
        domain=["游戏", "编程"],
        tags=["暖溪村", "购买种子", "种下"],
        memory_kind="procedure",
        importance=8,
    )

    results = await bucket_mgr.search(
        "农场游戏怎么买种子并种下",
        limit=10,
        record_stats=False,
    )
    ranked_ids = [item["id"] for item in results]

    assert procedure_id in ranked_ids
    if activity_id in ranked_ids:
        assert ranked_ids.index(procedure_id) < ranked_ids.index(activity_id)


@pytest.mark.asyncio
async def test_multi_token_fallback_rescues_cross_field_exact_coverage(bucket_mgr):
    bucket_mgr.fuzzy_threshold = 95
    bucket_mgr.multi_token_fallback = True
    bucket_mgr.multi_token_min_coverage = 0.4
    target_id = await bucket_mgr.create(
        content=(
            "蓝塔用于北区身份校验，中间省略若干背景说明。"
            "月门用于南区恢复入口。"
        ),
        name="双区恢复备忘",
        tags=["蓝塔", "月门"],
        importance=5,
        memory_kind="procedure",
    )
    query = "查蓝塔凭证以及月门操作"
    target = next(
        item
        for item in await bucket_mgr.list_all()
        if item["id"] == target_id
    )

    assert not bucket_mgr._calc_topic_match(query, target)["matched_in"]

    results = await bucket_mgr.search(query, limit=10, record_stats=False)
    match = next(item for item in results if item["id"] == target_id)

    assert match["retrieval_strategy"] == "multi_token_fallback"
    assert match["token_coverage"] >= 0.4
    assert {"蓝塔", "月门"} <= {
        token
        for hits in match["tokens_hit"].values()
        for token in hits
    }


@pytest.mark.asyncio
async def test_multi_token_fallback_does_not_rescue_one_generic_tag(bucket_mgr):
    bucket_mgr.fuzzy_threshold = 95
    bucket_mgr.multi_token_fallback = True
    bucket_mgr.multi_token_min_coverage = 0.2
    noise_id = await bucket_mgr.create(
        content="普通日常记录，与查询目标没有直接关系。",
        name="随手记",
        tags=["惩罚"],
        importance=5,
    )

    results = await bucket_mgr.search(
        "睡晚了要怎么计算惩罚",
        limit=10,
        record_stats=False,
    )

    assert noise_id not in {item["id"] for item in results}


@pytest.mark.asyncio
async def test_procedure_intent_boost_breaks_close_tie(bucket_mgr):
    fact_id = await bucket_mgr.create(
        content="先领取云莓种子，再选择苗圃播种。",
        name="云莓园播种",
        tags=["云莓园", "种子", "播种"],
        importance=7,
        memory_kind="fact",
    )
    procedure_id = await bucket_mgr.create(
        content="先领取云莓种子，再选择苗圃播种。",
        name="云莓园播种",
        tags=["云莓园", "种子", "播种"],
        importance=7,
        memory_kind="procedure",
    )
    bucket_mgr.procedure_intent_boost = 1.1

    results = await bucket_mgr.search(
        "云莓园种子怎么播种",
        limit=10,
        record_stats=False,
    )
    ranked_ids = [item["id"] for item in results]

    assert fact_id in ranked_ids
    assert procedure_id in ranked_ids
    assert ranked_ids.index(procedure_id) < ranked_ids.index(fact_id)


def test_runtime_fallback_overrides_are_clamped(bucket_mgr):
    bucket_mgr.apply_runtime_scoring_overrides({
        "multi_token_fallback": True,
        "multi_token_min_coverage": 4,
        "procedure_intent_boost": 9,
    })

    current = bucket_mgr.current_scoring_overrides()
    assert current["multi_token_fallback"] is True
    assert current["multi_token_min_coverage"] == 1.0
    assert current["procedure_intent_boost"] == 1.5

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

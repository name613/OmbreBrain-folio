import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def subject_env(bucket_mgr):
    fact_id = await bucket_mgr.create(
        content="服务使用独立身份路由。",
        name="部署事实",
        subject="Ombre Brain",
        memory_kind="fact",
        importance=7,
    )
    relationship_id = await bucket_mgr.create(
        content="一起维护这套长期记忆。",
        name="协作感受",
        subject="Ombre Brain",
        memory_kind="relationship",
        importance=7,
    )
    await bucket_mgr.create(
        content="另一个项目的普通记录。",
        name="无关记录",
        subject="Other Project",
        memory_kind="fact",
        importance=7,
    )
    return bucket_mgr, fact_id, relationship_id


@pytest.mark.asyncio
async def test_subject_only_match_is_searchable_and_explainable(subject_env):
    manager, fact_id, relationship_id = subject_env

    results = await manager.search("Ombre Brain", limit=10, record_stats=False)
    by_id = {item["id"]: item for item in results}

    assert fact_id in by_id
    assert relationship_id in by_id
    assert "subject" in by_id[fact_id]["matched_in"]
    assert by_id[fact_id]["field_scores"]["subject"] >= manager._MATCH_THRESHOLD


@pytest.mark.asyncio
async def test_precise_search_includes_subject_field(subject_env):
    manager, fact_id, _ = subject_env
    manager.precise_match_mode = True

    results = await manager.search("Ombre Brain", limit=10, record_stats=False)
    match = next(item for item in results if item["id"] == fact_id)

    assert "subject" in match["matched_in"]
    assert match["tokens_hit"]["subject"] == ["Ombre", "Brain"]


@pytest.mark.asyncio
async def test_technical_query_ranks_fact_above_same_subject_relationship(subject_env):
    manager, fact_id, relationship_id = subject_env

    results = await manager.search("Ombre Brain 怎么配置", limit=10, record_stats=False)
    ranked_ids = [item["id"] for item in results]

    assert fact_id in ranked_ids
    assert relationship_id in ranked_ids
    assert ranked_ids.index(fact_id) < ranked_ids.index(relationship_id)

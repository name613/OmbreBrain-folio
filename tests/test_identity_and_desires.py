import json
import asyncio

import pytest
from datetime import datetime, timezone

from desire_engine import DesireEngine
from identity_scope import can_access
from bucket_manager import BucketManager
from memory_context import feel_temporal_lens


def test_named_identity_owner_is_private_even_when_key_is_removed():
    metadata = {"created_by": "keke", "tags": []}
    assert can_access(metadata, "keke", set())
    assert not can_access(metadata, "cc", set())


def test_legacy_shared_creator_remains_visible():
    assert can_access({"created_by": "ai", "tags": []}, "cc", {"cc", "keke"})
    assert can_access({"tags": []}, "keke", {"cc", "keke"})


def test_legacy_identity_tag_is_still_isolated():
    metadata = {"created_by": "ai", "tags": ["keke"]}
    assert can_access(metadata, "keke", {"cc", "keke"})
    assert not can_access(metadata, "cc", {"cc", "keke"})


def test_desires_are_identity_scoped_and_persist(tmp_path):
    engine = DesireEngine(str(tmp_path))
    mine = engine.upsert("cc", "把记忆检索调准", tension=0.8, priority=9)
    engine.upsert("keke", "整理关系记忆", tension=0.6, priority=8)

    reloaded = DesireEngine(str(tmp_path))
    assert [item["id"] for item in reloaded.list("cc")] == [mine["id"]]
    assert all(item["title"] != "整理关系记忆" for item in reloaded.list("cc", True))

    updated = reloaded.set_status("cc", mine["id"], "fulfilled", "检索测试通过")
    assert updated["status"] == "fulfilled"
    assert reloaded.list("cc") == []
    assert reloaded.list("cc", include_closed=True)[0]["progress"] == "检索测试通过"

    raw = json.loads((tmp_path / "desires.json").read_text(encoding="utf-8"))
    assert set(raw["identities"]) == {"cc", "keke"}
    assert raw["version"] == 2
    assert raw["identities"]["cc"][0]["owner"] == "cc"
    assert raw["identities"]["keke"][0]["owner"] == "keke"


def test_desire_update_cannot_cross_identity(tmp_path):
    engine = DesireEngine(str(tmp_path))
    item = engine.upsert("keke", "私有牵引")
    with pytest.raises(KeyError):
        engine.set_status("cc", item["id"], "released")


def test_desire_row_owner_is_a_second_isolation_boundary(tmp_path):
    path = tmp_path / "desires.json"
    path.write_text(json.dumps({
        "version": 2,
        "identities": {
            "cc": [{"id": "wrong-owner", "owner": "keke", "title": "不该被 cc 读取"}],
        },
    }), encoding="utf-8")
    engine = DesireEngine(str(tmp_path))
    assert engine.list("cc", include_closed=True) == []
    with pytest.raises(KeyError):
        engine.set_status("cc", "wrong-owner", "released")


def test_legacy_desire_without_owner_inherits_its_identity_partition(tmp_path):
    path = tmp_path / "desires.json"
    path.write_text(json.dumps({
        "version": 1,
        "identities": {
            "cc": [{"id": "legacy", "title": "旧牵引", "status": "active"}],
        },
    }), encoding="utf-8")
    engine = DesireEngine(str(tmp_path))
    assert engine.list("cc")[0]["owner"] == "cc"
    updated = engine.set_status("cc", "legacy", "paused")
    assert updated["owner"] == "cc"


def test_feel_temporal_lens_marks_old_state_as_evidence_not_current_emotion():
    lens = feel_temporal_lens(
        "2026-07-19T08:00:00+00:00",
        now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
    )
    assert "3 天前记录" in lens
    assert "不等于此刻情绪" in lens
    assert "不要直接续写当时状态" in lens


def test_memory_kind_intent_reranks_tool_facts_above_reflection():
    query = "服务器怎么配置环境变量和 token"
    fact = BucketManager.kind_multiplier(query, {"memory_kind": "procedure"})
    reflection = BucketManager.kind_multiplier(query, {"memory_kind": "reflection"})
    legacy = BucketManager.kind_multiplier(query, {})
    assert fact > legacy > reflection


def test_explicit_memory_kind_filter_is_strict(tmp_path):
    config = {
        "buckets_dir": str(tmp_path / "buckets"),
        "matching": {"fuzzy_threshold": 50, "max_results": 10},
        "wikilink": {"enabled": False},
        "scoring_weights": {"content_weight": 1.0},
    }
    async def scenario():
        manager = BucketManager(config)
        fact_id = await manager.create(
            "Zeabur 端口配置", name="部署方法", memory_kind="procedure", subject="Ombre Brain",
        )
        await manager.create("想到部署时觉得很温暖", name="部署感受", memory_kind="reflection")
        results = await manager.search("部署", memory_kinds=["procedure"])
        assert [item["id"] for item in results] == [fact_id]
        saved = await manager.get(fact_id)
        assert saved["metadata"]["subject"] == "Ombre Brain"
        await manager.update(fact_id, created_by="cc")
        assert (await manager.get(fact_id))["metadata"]["created_by"] == "cc"

    asyncio.run(scenario())

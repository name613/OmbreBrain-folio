import pytest

from memory_review import assess_stored_memory


def test_well_anchored_memory_does_not_enter_review_queue():
    report = assess_stored_memory(
        {
            "name": "北星网关恢复步骤",
            "memory_kind": "procedure",
            "subject": "北星网关",
            "tags": ["北星网关", "快照", "恢复"],
        },
        "先暂停写入，然后校验快照，最后恢复服务。",
        bucket_id="abc123",
    )

    assert report["review_required"] is False
    assert report["reason_codes"] == []
    assert report["priority"] == 0


def test_opaque_legacy_memory_gets_explainable_reasons_without_mutation():
    metadata = {
        "name": "abcdef123456",
        "memory_kind": "",
        "subject": "",
        "tags": ["AI"],
    }

    report = assess_stored_memory(
        metadata,
        "那天记录了一些感受。",
        bucket_id="abcdef123456",
    )

    assert set(report["reason_codes"]) == {
        "title_opaque",
        "memory_kind_missing",
        "tags_generic_only",
        "tags_sparse",
    }
    assert report["priority"] == 10
    assert metadata == {
        "name": "abcdef123456",
        "memory_kind": "",
        "subject": "",
        "tags": ["AI"],
    }


def test_subject_and_step_reasons_only_apply_to_anchored_memory_kinds():
    procedure = assess_stored_memory(
        {
            "name": "服务恢复",
            "memory_kind": "procedure",
            "subject": "",
            "tags": ["服务", "恢复", "检查"],
        },
        "恢复服务并检查状态。",
    )
    reflection = assess_stored_memory(
        {
            "name": "恢复后的想法",
            "memory_kind": "reflection",
            "subject": "",
            "tags": ["恢复", "协作", "边界"],
        },
        "这次经历让我更理解协作边界。",
    )

    assert "subject_missing" in procedure["reason_codes"]
    assert "procedure_steps_unclear" in procedure["reason_codes"]
    assert "subject_missing" not in reflection["reason_codes"]
    assert "procedure_steps_unclear" not in reflection["reason_codes"]


def test_overloaded_tags_are_flagged_but_not_trimmed():
    tags = ["项目", "部署", "恢复", "检查", "快照", "回滚", "VPS"]
    report = assess_stored_memory(
        {
            "name": "部署恢复约定",
            "memory_kind": "commitment",
            "subject": "部署流程",
            "tags": tags,
        },
        "每次切换前都先验证快照。",
    )

    assert report["reason_codes"] == ["tags_overloaded"]
    assert tags == ["项目", "部署", "恢复", "检查", "快照", "回滚", "VPS"]


@pytest.mark.asyncio
async def test_review_queue_is_owner_scoped_and_excludes_shared(monkeypatch):
    import server

    async def fake_list_all(include_archive=False):
        assert include_archive is False
        return [
            {
                "id": "qiqi-memory",
                "metadata": {
                    "name": "abcdef123456",
                    "created_by": "qiqi",
                    "tags": ["AI"],
                },
                "content": "callback?token=secret-value-123",
            },
            {
                "id": "keke-memory",
                "metadata": {
                    "name": "123456abcdef",
                    "created_by": "keke",
                    "tags": ["AI"],
                },
                "content": "private keke memory",
            },
            {
                "id": "shared-memory",
                "metadata": {
                    "name": "fedcba654321",
                    "created_by": "keke",
                    "share_scope": "shared",
                    "tags": ["AI"],
                },
                "content": "shared but still not assigned to qiqi for review",
            },
        ]

    monkeypatch.setattr(server.bucket_mgr, "list_all", fake_list_all)
    items, total = await server._collect_review_candidates(
        "qiqi",
        reason="title_opaque",
        limit=20,
    )

    assert total == 1
    assert [item["id"] for item in items] == ["qiqi-memory"]
    assert "secret-value-123" not in items[0]["content_preview"]

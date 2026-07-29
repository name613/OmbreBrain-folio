import json

from dehydrator import Dehydrator
from memory_contract import prepare_memory_candidate
from utils import redact_sensitive_text


def _dehydrator(tmp_path):
    return Dehydrator({
        "buckets_dir": str(tmp_path),
        "dehydration": {"api_key": ""},
    })


def test_candidate_contract_keeps_specific_tags_and_removes_generic_ones():
    candidate, report = prepare_memory_candidate({
        "name": "[[北星网关恢复]]",
        "subject": "[[北星网关]]",
        "memory_kind": "procedure",
        "tags": [
            "系统", "北星网关", "快照", "健康检查",
            "恢复", "回滚", "校验", "演练", "恢复",
        ],
        "content": "1. 校验快照。2. 恢复数据。3. 运行健康检查。",
    })

    assert candidate["name"] == "北星网关恢复"
    assert candidate["subject"] == "北星网关"
    assert candidate["tags"] == [
        "北星网关", "快照", "健康检查", "恢复", "回滚", "校验",
    ]
    assert "generic_tags_removed" in report["warning_codes"]
    assert "tags_trimmed" in report["warning_codes"]


def test_candidate_contract_flags_opaque_metadata_without_blocking():
    candidate, report = prepare_memory_candidate({
        "name": "3f8d2a7b9c10",
        "content": "一次普通记录。",
        "tags": ["日常"],
        "memory_kind": "biography",
    })

    assert candidate["memory_kind"] == "episode"
    assert report["status"] == "needs_review"
    assert {
        "title_opaque",
        "subject_missing",
        "memory_kind_defaulted",
        "generic_tags_removed",
        "tags_sparse",
    } <= set(report["warning_codes"])


def test_candidate_contract_redacts_generated_credentials():
    candidate, report = prepare_memory_candidate({
        "name": "部署入口",
        "subject": "测试服务",
        "memory_kind": "fact",
        "tags": ["测试服务", "部署", "入口"],
        "content": (
            "API key: sk-example123456789 "
            "https://example.test/callback?token=secret-value-123"
        ),
    })

    assert "sk-example123456789" not in candidate["content"]
    assert "secret-value-123" not in candidate["content"]
    assert report["redacted"] is True
    assert "credential_redacted" in report["warning_codes"]


def test_candidate_contract_flags_unordered_procedure():
    _, report = prepare_memory_candidate({
        "name": "北星网关恢复",
        "subject": "北星网关",
        "memory_kind": "procedure",
        "tags": ["北星网关", "恢复", "健康检查"],
        "content": "恢复快照并检查服务状态。",
    })

    assert "procedure_steps_unclear" in report["warning_codes"]


def test_digest_parser_returns_contract_feedback_and_safe_content(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    raw = json.dumps([{
        "name": "部署入口",
        "content": "password: example-password-123",
        "domain": ["网络"],
        "tags": ["系统", "部署"],
        "memory_kind": "fact",
        "subject": "",
    }], ensure_ascii=False)

    item = dehydrator._parse_digest(raw)[0]

    assert "example-password-123" not in item["content"]
    assert item["_write_contract"]["review_required"] is True
    assert "credential_redacted" in item["_write_contract"]["warning_codes"]


def test_redaction_masks_private_key_blocks():
    text = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "not-a-real-key\n"
        "-----END OPENSSH PRIVATE KEY-----"
    )

    assert redact_sensitive_text(text) == "[REDACTED PRIVATE KEY]"

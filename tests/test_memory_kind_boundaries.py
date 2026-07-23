import json

from dehydrator import ANALYZE_PROMPT, DIGEST_PROMPT, Dehydrator


def _dehydrator(tmp_path):
    return Dehydrator({
        "buckets_dir": str(tmp_path),
        "dehydration": {"api_key": ""},
    })


def test_digest_parser_preserves_kind_and_subject(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    raw = json.dumps([{
        "name": "部署配置",
        "content": "Zeabur 使用环境变量配置服务。",
        "domain": ["数字"],
        "valence": 0.5,
        "arousal": 0.2,
        "tags": ["Zeabur", "环境变量"],
        "importance": 7,
        "memory_kind": "procedure",
        "subject": "[[Ombre Brain]]",
    }], ensure_ascii=False)

    item = dehydrator._parse_digest(raw)[0]

    assert item["memory_kind"] == "procedure"
    assert item["subject"] == "Ombre Brain"


def test_digest_parser_uses_safe_kind_for_unknown_value(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    raw = json.dumps([{
        "name": "未知分类",
        "content": "模型返回了不支持的记忆类型。",
        "memory_kind": "biography",
        "subject": "测试对象",
    }], ensure_ascii=False)

    item = dehydrator._parse_digest(raw)[0]

    assert item["memory_kind"] == "episode"
    assert item["subject"] == "测试对象"


def test_prompts_define_fact_relationship_boundary():
    for prompt in (ANALYZE_PROMPT, DIGEST_PROMPT):
        assert "仅仅提到某个人" in prompt
        assert "双方关系、互动模式或共同经历" in prompt
        assert "不要因为文字温柔就把技术事实标成 relationship/reflection" in prompt

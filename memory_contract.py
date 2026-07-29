"""Non-destructive validation for new AI-generated memory candidates."""

from __future__ import annotations

import re
from typing import Any

from utils import redact_sensitive_text, strip_wikilinks


MEMORY_KINDS = {
    "fact",
    "procedure",
    "commitment",
    "preference",
    "relationship",
    "episode",
    "reflection",
    "desire",
}

GENERIC_TAGS = {
    "ai",
    "其他",
    "事情",
    "内容",
    "记录",
    "回忆",
    "想法",
    "生活",
    "情感",
    "系统",
    "游戏",
    "日常",
    "未分类",
}

GENERIC_TITLES = {
    "未命名",
    "无标题",
    "新记忆",
    "记忆",
    "记录",
    "随手记",
    "untitled",
    "memory",
    "note",
}

WARNING_MESSAGES = {
    "credential_redacted": "候选中检测到凭据，已在入库前隐藏具体值",
    "generic_tags_removed": "已移除不能区分这条记忆的宽泛标签",
    "memory_kind_defaulted": "记忆类型无效，暂按 episode 保存，请复核",
    "procedure_steps_unclear": "这是操作方法，但正文缺少清晰的步骤顺序",
    "subject_missing": "缺少明确主体，之后按人名、项目名或对象名检索可能较弱",
    "tags_sparse": "有效标签少于 3 个，建议补充可区分的名称或操作词",
    "tags_trimmed": "标签超过 6 个，已只保留前 6 个",
    "title_missing": "缺少可读标题，之后按标题检索可能较弱",
    "title_opaque": "标题像内部编号或泛称，建议改成能直接搜索的短标题",
}

_OPAQUE_TITLE_RE = re.compile(
    r"^(?:[0-9a-f]{12}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_PROCEDURE_STEP_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+[.)、]|步骤\s*\d+)|先.+(?:再|然后|最后)",
    re.DOTALL,
)


def _text(value: Any, limit: int) -> str:
    cleaned = strip_wikilinks(str(value or "")).strip()
    return cleaned[:limit]


def _values(value: Any) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,，、\n]+", value)
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe(values: list[str], *, limit: int) -> list[str]:
    output = []
    seen = set()
    for value in values:
        cleaned = strip_wikilinks(value).strip()[:40]
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
        if len(output) >= limit:
            break
    return output


def prepare_memory_candidate(
    candidate: dict[str, Any],
    *,
    redact_generated_text: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize one new candidate and return review hints without touching stored data."""
    output = dict(candidate or {})
    warning_codes: list[str] = []

    def warn(code: str) -> None:
        if code not in warning_codes:
            warning_codes.append(code)

    title_key = "name" if "name" in output else "suggested_name"
    title = _text(output.get(title_key, ""), 40)
    output[title_key] = title
    if not title:
        warn("title_missing")
    elif (
        title.casefold() in GENERIC_TITLES
        or _OPAQUE_TITLE_RE.fullmatch(title)
    ):
        warn("title_opaque")

    subject = _text(output.get("subject", ""), 120)
    output["subject"] = subject
    if not subject:
        warn("subject_missing")

    raw_kind = str(output.get("memory_kind", "")).strip().lower()
    if raw_kind not in MEMORY_KINDS:
        output["memory_kind"] = "episode"
        warn("memory_kind_defaulted")
    else:
        output["memory_kind"] = raw_kind

    raw_tags = _dedupe(_values(output.get("tags", [])), limit=64)
    tags = [
        tag
        for tag in raw_tags
        if tag.casefold() not in GENERIC_TAGS
    ]
    if len(tags) != len(raw_tags):
        warn("generic_tags_removed")
    if len(tags) > 6:
        tags = tags[:6]
        warn("tags_trimmed")
    if len(tags) < 3:
        warn("tags_sparse")
    output["tags"] = tags

    output["domain"] = _dedupe(
        _values(output.get("domain", [])),
        limit=3,
    )

    redacted = False
    if redact_generated_text:
        for field, limit in (
            (title_key, 40),
            ("subject", 120),
            ("content", 50000),
            ("summary", 600),
            ("source_excerpt", 600),
        ):
            if field not in output:
                continue
            original = str(output.get(field, ""))
            safe = redact_sensitive_text(original)
            output[field] = safe[:limit]
            redacted = redacted or safe != original

        safe_tags = []
        for tag in output["tags"]:
            safe = redact_sensitive_text(tag)
            redacted = redacted or safe != tag
            safe_tags.append(safe[:40])
        output["tags"] = _dedupe(safe_tags, limit=6)
        if len(output["tags"]) < 3:
            warn("tags_sparse")

    if redacted:
        warn("credential_redacted")

    content = str(output.get("content", ""))
    if (
        output["memory_kind"] == "procedure"
        and content
        and not _PROCEDURE_STEP_RE.search(content)
    ):
        warn("procedure_steps_unclear")

    report = {
        "status": "needs_review" if warning_codes else "ready",
        "review_required": bool(warning_codes),
        "warning_codes": warning_codes,
        "warnings": [
            WARNING_MESSAGES[code]
            for code in warning_codes
        ],
        "redacted": redacted,
    }
    return output, report

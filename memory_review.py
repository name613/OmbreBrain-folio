"""Read-only quality signals for already stored memories."""

from __future__ import annotations

import re
from typing import Any

from memory_contract import GENERIC_TAGS, GENERIC_TITLES, MEMORY_KINDS
from utils import strip_wikilinks


REVIEW_REASON_MESSAGES = {
    "title_missing": "缺少可直接搜索的标题",
    "title_opaque": "标题像内部编号或宽泛占位词",
    "memory_kind_missing": "缺少记忆类型",
    "memory_kind_invalid": "记忆类型不在当前类型表中",
    "subject_missing": "稳定事实或约定缺少明确主体",
    "tags_sparse": "可区分标签少于 3 个",
    "tags_overloaded": "标签超过 6 个，检索主题可能发散",
    "tags_generic_only": "标签只有宽泛词，不能形成检索锚点",
    "procedure_steps_unclear": "操作方法缺少清晰的步骤顺序",
}

_OPAQUE_TITLE_RE = re.compile(
    r"^(?:[0-9a-f]{12,40}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_PROCEDURE_STEP_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+[.)、]|步骤\s*\d+)|先.+(?:再|然后|最后)",
    re.DOTALL,
)
_SUBJECT_ANCHORED_KINDS = {
    "fact",
    "procedure",
    "commitment",
    "preference",
    "relationship",
}
_REASON_WEIGHTS = {
    "title_missing": 4,
    "title_opaque": 4,
    "memory_kind_missing": 3,
    "memory_kind_invalid": 3,
    "subject_missing": 2,
    "tags_generic_only": 2,
    "procedure_steps_unclear": 2,
    "tags_sparse": 1,
    "tags_overloaded": 1,
}


def _values(value: Any) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,，、\n]+", value)
    if not isinstance(value, (list, tuple, set)):
        return []
    output = []
    seen = set()
    for item in value:
        cleaned = strip_wikilinks(str(item or "")).strip()
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def assess_stored_memory(
    metadata: dict[str, Any] | None,
    content: str = "",
    *,
    bucket_id: str = "",
) -> dict[str, Any]:
    """Describe review reasons without normalizing or changing stored data."""
    metadata = metadata or {}
    reason_codes: list[str] = []

    def add(code: str) -> None:
        if code not in reason_codes:
            reason_codes.append(code)

    title = strip_wikilinks(str(metadata.get("name", "") or "")).strip()
    if not title:
        add("title_missing")
    elif (
        title.casefold() in GENERIC_TITLES
        or title == bucket_id
        or _OPAQUE_TITLE_RE.fullmatch(title)
    ):
        add("title_opaque")

    memory_kind = str(metadata.get("memory_kind", "") or "").strip().lower()
    if not memory_kind:
        add("memory_kind_missing")
    elif memory_kind not in MEMORY_KINDS:
        add("memory_kind_invalid")

    subject = strip_wikilinks(str(metadata.get("subject", "") or "")).strip()
    if memory_kind in _SUBJECT_ANCHORED_KINDS and not subject:
        add("subject_missing")

    tags = _values(metadata.get("tags", []))
    discriminative_tags = [
        tag for tag in tags if tag.casefold() not in GENERIC_TAGS
    ]
    if tags and not discriminative_tags:
        add("tags_generic_only")
    if len(discriminative_tags) < 3:
        add("tags_sparse")
    if len(tags) > 6:
        add("tags_overloaded")

    clean_content = strip_wikilinks(str(content or "")).strip()
    if (
        memory_kind == "procedure"
        and clean_content
        and not _PROCEDURE_STEP_RE.search(clean_content)
    ):
        add("procedure_steps_unclear")

    return {
        "review_required": bool(reason_codes),
        "reason_codes": reason_codes,
        "reasons": [REVIEW_REASON_MESSAGES[code] for code in reason_codes],
        "priority": sum(_REASON_WEIGHTS[code] for code in reason_codes),
    }

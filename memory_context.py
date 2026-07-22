"""Small helpers for presenting recalled memories in the right time frame."""

from datetime import datetime, timezone


def _parse_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def feel_temporal_lens(created: str, now: datetime | None = None) -> str:
    """Describe a feel as past evidence, never as the caller's current state."""
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    parsed = _parse_datetime(created)
    if parsed is None:
        age = "记录时间不明"
    else:
        days = max(0, (reference.astimezone(timezone.utc).date() - parsed.date()).days)
        age = "今天记录" if days == 0 else f"{days} 天前记录"
    return (
        f"[时间透镜: {age}；这是过去感受的证据，不等于此刻情绪。"
        "可用于识别经历与模式，但请根据当前对话重新判断，不要直接续写当时状态。]"
    )

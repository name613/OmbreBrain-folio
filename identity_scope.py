"""Backward-compatible identity access rules for memory metadata."""

SHARED_CREATORS = frozenset({"", "ai", "user", "import", "system"})


def can_access(metadata: dict, caller: str, known_identities: set[str]) -> bool:
    metadata = metadata or {}
    caller = str(caller or "ai")
    owner = str(metadata.get("created_by", "") or "")

    # Any named AI owner is private even if its key is temporarily removed.
    if owner not in SHARED_CREATORS and owner != caller:
        return False

    known = {str(value) for value in known_identities if value and value != "ai"}
    foreign_tags = known - {caller}
    return not bool(foreign_tags & set(metadata.get("tags", []) or []))

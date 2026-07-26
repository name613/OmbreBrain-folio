"""Backward-compatible identity access rules for memory metadata."""

LEGACY_CREATORS = frozenset({"", "ai", "user", "import", "system"})


def canonical_identity(identity: str, aliases: dict[str, str] | None = None) -> str:
    value = str(identity or "").strip()
    aliases = aliases or {}
    seen = set()
    while value in aliases and value not in seen:
        seen.add(value)
        value = str(aliases[value] or "").strip()
    return value


def can_access(
    metadata: dict,
    caller: str,
    known_identities: set[str],
    legacy_owner: str | None = None,
    aliases: dict[str, str] | None = None,
) -> bool:
    metadata = metadata or {}
    aliases = aliases or {}
    caller = canonical_identity(caller or "ai", aliases)

    if str(metadata.get("share_scope", "")).strip().lower() == "shared":
        return True

    known = {
        canonical_identity(value, aliases)
        for value in known_identities
        if value
    }
    known.discard("ai")
    if legacy_owner:
        known.add(canonical_identity(legacy_owner, aliases))
    known.add(caller)

    identity_tags = {
        canonical_identity(tag, aliases)
        for tag in (metadata.get("tags", []) or [])
        if canonical_identity(tag, aliases) in known
    }

    raw_owner = str(metadata.get("created_by", "") or "").strip()
    if raw_owner in LEGACY_CREATORS:
        # A legacy identity tag is stronger evidence than a generic creator.
        if len(identity_tags) == 1:
            owner = next(iter(identity_tags))
        elif legacy_owner:
            owner = canonical_identity(legacy_owner, aliases)
        else:
            owner = ""
    else:
        owner = canonical_identity(raw_owner, aliases)

    # No configured legacy owner preserves the original shared compatibility.
    if owner and owner != caller:
        return False

    # Multiple or contradictory identity tags fail closed.
    return not bool(identity_tags - {caller})

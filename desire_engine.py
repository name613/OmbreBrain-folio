"""Identity-scoped persistent drives, kept separate from semantic memory."""

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DesireEngine:
    VALID_STATUS = {"active", "paused", "fulfilled", "released"}

    def __init__(self, buckets_dir: str):
        self.path = os.path.join(buckets_dir, "desires.json")
        self._lock = threading.RLock()

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {"version": 1, "identities": {}}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {"version": 1, "identities": {}}

    def _write(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="desires-", suffix=".tmp", dir=os.path.dirname(self.path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def list(self, identity: str, include_closed: bool = False) -> list[dict]:
        with self._lock:
            items = list(self._read().get("identities", {}).get(identity, []))
        if not include_closed:
            items = [item for item in items if item.get("status", "active") in {"active", "paused"}]
        return sorted(
            items,
            key=lambda item: (
                item.get("status") == "active",
                float(item.get("tension", 0)),
                int(item.get("priority", 0)),
                item.get("updated", ""),
            ),
            reverse=True,
        )

    def upsert(
        self,
        identity: str,
        title: str,
        why: str = "",
        desire_id: str = "",
        tension: float = 0.5,
        priority: int = 5,
        progress: str = "",
        status: str = "active",
    ) -> dict:
        title = str(title or "").strip()
        if not title:
            raise ValueError("title is required")
        status = str(status or "active").lower()
        if status not in self.VALID_STATUS:
            raise ValueError(f"invalid status: {status}")
        now = _now()
        with self._lock:
            data = self._read()
            identities = data.setdefault("identities", {})
            items = identities.setdefault(identity, [])
            item = next((row for row in items if row.get("id") == desire_id), None)
            if item is None:
                item = {"id": uuid.uuid4().hex[:12], "created": now}
                items.append(item)
            item.update({
                "title": title[:160],
                "why": str(why or "").strip()[:1000],
                "tension": max(0.0, min(1.0, float(tension))),
                "priority": max(1, min(10, int(priority))),
                "progress": str(progress or "").strip()[:1000],
                "status": status,
                "updated": now,
            })
            self._write(data)
            return dict(item)

    def set_status(self, identity: str, desire_id: str, status: str, progress: str = "") -> dict:
        status = str(status or "").lower()
        if status not in self.VALID_STATUS:
            raise ValueError(f"invalid status: {status}")
        with self._lock:
            data = self._read()
            items = data.get("identities", {}).get(identity, [])
            item = next((row for row in items if row.get("id") == desire_id), None)
            if item is None:
                raise KeyError(desire_id)
            item["status"] = status
            if progress:
                item["progress"] = str(progress).strip()[:1000]
            item["updated"] = _now()
            self._write(data)
            return dict(item)

    def remove(self, identity: str, desire_id: str) -> bool:
        with self._lock:
            data = self._read()
            items = data.get("identities", {}).get(identity, [])
            kept = [row for row in items if row.get("id") != desire_id]
            if len(kept) == len(items):
                return False
            data["identities"][identity] = kept
            self._write(data)
            return True

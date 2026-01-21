import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CHAT_DIR_NAME = "chat_history"


def _chat_dir() -> Path:
    return Path(__file__).resolve().parent / CHAT_DIR_NAME


def ensure_chat_dir() -> Path:
    chat_dir = _chat_dir()
    chat_dir.mkdir(parents=True, exist_ok=True)
    return chat_dir


def _chat_path(chat_id: str) -> Path:
    return ensure_chat_dir() / f"{chat_id}.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_chat_name(now: Optional[datetime] = None) -> str:
    if now is None:
        now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def new_chat_id(now: Optional[datetime] = None) -> str:
    if now is None:
        now = datetime.now()
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def load_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    path = _chat_path(chat_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_chat(
    chat_id: str,
    name: str,
    messages: List[Dict[str, Any]],
    whitelist: str,
) -> Dict[str, Any]:
    path = _chat_path(chat_id)
    existing = load_chat(chat_id) or {}
    now = _now_iso()
    payload = {
        "id": chat_id,
        "name": name or "Untitled",
        "whitelist": whitelist,
        "created_at": existing.get("created_at", now),
        "updated_at": now,
        "messages": messages,
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def delete_chat(chat_id: str) -> bool:
    path = _chat_path(chat_id)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def list_chats() -> List[Dict[str, Any]]:
    chat_dir = ensure_chat_dir()
    chats = []
    for path in chat_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        chat_id = data.get("id") or path.stem
        updated_at = data.get("updated_at") or data.get("created_at")
        chats.append(
            {
                "id": chat_id,
                "name": data.get("name") or "Untitled",
                "whitelist": data.get("whitelist"),
                "created_at": data.get("created_at"),
                "updated_at": updated_at,
                "_mtime": path.stat().st_mtime,
            }
        )

    def sort_key(item: Dict[str, Any]) -> float:
        parsed = _parse_iso(item.get("updated_at")) or _parse_iso(item.get("created_at"))
        if parsed:
            return parsed.timestamp()
        return item.get("_mtime", 0.0)

    chats.sort(key=sort_key, reverse=True)
    return chats

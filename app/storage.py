"""Local save file. Keeps your plan and streak between sessions.

Deliberately a plain JSON file in the project folder — no database, nothing
leaves your machine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

SAVE_PATH = Path(__file__).resolve().parent.parent / "my_data.json"

DEFAULT: Dict[str, Any] = {
    "profile": {},
    "workout_plan": "",
    "diet_plan": "",
    "progress": {},
    "history": [],  # past plans, newest first
}


def load() -> Dict[str, Any]:
    """Read the save file, falling back to defaults if it's missing or corrupt."""
    if not SAVE_PATH.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT))
    merged = json.loads(json.dumps(DEFAULT))
    if isinstance(data, dict):
        merged.update(data)
    return merged


def save(data: Dict[str, Any]) -> bool:
    """Write the save file. Returns False rather than raising if the disk says no."""
    try:
        SAVE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def archive_plan(data: Dict[str, Any], plan: str, label: str) -> None:
    """Push the current plan onto the history stack, keeping the last ten."""
    if not plan:
        return
    data.setdefault("history", []).insert(0, {"label": label, "plan": plan})
    data["history"] = data["history"][:10]

"""Small, durable desktop-only preference store kept out of quota history."""

import json
from copy import deepcopy
from pathlib import Path


PANEL_IDS = ("five-hour", "weekly", "pace", "resets", "account", "history")
DEFAULT_PREFERENCES = {
    "tray_indicator": True,
    "panels": {
        "five-hour": {"visible": True, "column": 1, "row": 1, "width": 2, "height": 1},
        "weekly": {"visible": True, "column": 3, "row": 1, "width": 2, "height": 1},
        "pace": {"visible": True, "column": 1, "row": 2, "width": 2, "height": 1},
        "resets": {"visible": True, "column": 3, "row": 2, "width": 1, "height": 1},
        "account": {"visible": True, "column": 4, "row": 2, "width": 1, "height": 1},
        "history": {"visible": True, "column": 1, "row": 3, "width": 4, "height": 2},
    },
}


def default_preferences():
    return deepcopy(DEFAULT_PREFERENCES)


def preferences_path(data_dir):
    return Path(data_dir) / "desktop-preferences.json"


def _validated(value):
    defaults = default_preferences()
    if not isinstance(value, dict):
        return defaults
    defaults["tray_indicator"] = bool(value.get("tray_indicator", True))
    source_panels = value.get("panels", {})
    if not isinstance(source_panels, dict):
        return defaults
    for panel_id, panel in defaults["panels"].items():
        candidate = source_panels.get(panel_id, {})
        if not isinstance(candidate, dict):
            continue
        panel["visible"] = bool(candidate.get("visible", panel["visible"]))
        for key, maximum in (("column", 4), ("row", 20), ("width", 4), ("height", 4)):
            value = candidate.get(key, panel[key])
            if isinstance(value, int) and 1 <= value <= maximum:
                panel[key] = value
    return defaults


def load_preferences(data_dir):
    try:
        with preferences_path(data_dir).open(encoding="utf-8") as handle:
            return _validated(json.load(handle))
    except (OSError, ValueError, TypeError):
        return default_preferences()


def save_preferences(data_dir, preferences):
    path = preferences_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _validated(preferences)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return normalized

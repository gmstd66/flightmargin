"""Small, durable dashboard preference store kept out of quota history."""

import json
from copy import deepcopy
from pathlib import Path


PANEL_IDS = ("five-hour", "weekly", "pace", "resets", "account", "history")
LAYOUT_SCHEMA = 4
DEFAULT_PREFERENCES = {
    "layout_schema": LAYOUT_SCHEMA,
    "tray_indicator": True,
    "panels": {panel_id: True for panel_id in PANEL_IDS},
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
    if value.get("layout_schema") != LAYOUT_SCHEMA:
        return defaults
    source_panels = value.get("panels", {})
    if not isinstance(source_panels, dict):
        return defaults
    for panel_id in PANEL_IDS:
        candidate = source_panels.get(panel_id)
        if isinstance(candidate, bool):
            defaults["panels"][panel_id] = candidate
    return defaults


def show_all_panels(preferences):
    normalized = _validated(preferences)
    normalized["panels"] = {panel_id: True for panel_id in PANEL_IDS}
    return normalized


def load_preferences(data_dir):
    try:
        with preferences_path(data_dir).open(encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError, TypeError):
        return default_preferences()
    normalized = _validated(stored)
    if normalized != stored:
        try:
            save_preferences(data_dir, normalized)
        except OSError:
            pass
    return normalized


def save_preferences(data_dir, preferences):
    path = preferences_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _validated(preferences)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return normalized

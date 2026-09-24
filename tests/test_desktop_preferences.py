import json

from app.desktop_preferences import (
    PANEL_IDS,
    default_preferences,
    load_preferences,
    preferences_path,
    save_preferences,
)


def test_default_preferences_cover_each_panel_and_enable_tray_indicator():
    preferences = default_preferences()
    assert preferences["layout_schema"] == 2
    assert preferences["tray_indicator"] is True
    assert set(preferences["panels"]) == set(PANEL_IDS)


def test_preferences_round_trip_and_preserve_hidden_panel(tmp_path):
    preferences = default_preferences()
    preferences["tray_indicator"] = False
    preferences["panels"]["history"]["visible"] = False
    save_preferences(tmp_path, preferences)
    assert load_preferences(tmp_path)["tray_indicator"] is False
    assert load_preferences(tmp_path)["panels"]["history"]["visible"] is False


def test_corrupt_preferences_fall_back_to_defaults(tmp_path):
    preferences_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert load_preferences(tmp_path) == default_preferences()


def test_preferences_clamp_panel_grid_values(tmp_path):
    preferences = default_preferences()
    preferences["panels"]["weekly"]["width"] = 99
    save_preferences(tmp_path, preferences)
    assert load_preferences(tmp_path)["panels"]["weekly"]["width"] == 2


def test_legacy_preferences_keep_unrelated_tray_choice(tmp_path):
    save_preferences(tmp_path, {"tray_indicator": False, "panels": {}})
    assert load_preferences(tmp_path)["tray_indicator"] is False
    assert load_preferences(tmp_path)["layout_schema"] == 2

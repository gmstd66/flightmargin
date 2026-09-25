import json

from app.desktop_preferences import (
    LAYOUT_SCHEMA,
    PANEL_MINIMUMS,
    PANEL_IDS,
    default_preferences,
    load_preferences,
    preferences_path,
    save_preferences,
)


def test_default_preferences_cover_each_panel_and_enable_tray_indicator():
    preferences = default_preferences()
    assert preferences["layout_schema"] == LAYOUT_SCHEMA == 3
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


def test_quota_panels_enforce_responsive_minimum_width(tmp_path):
    preferences = default_preferences()
    preferences["panels"]["five-hour"]["width"] = 1
    preferences["panels"]["weekly"]["width"] = 1
    save_preferences(tmp_path, preferences)
    loaded = load_preferences(tmp_path)
    assert loaded["panels"]["five-hour"]["width"] == PANEL_MINIMUMS["five-hour"]["width"] == 2
    assert loaded["panels"]["weekly"]["width"] == PANEL_MINIMUMS["weekly"]["width"] == 2


def test_v2_layout_migrates_to_compact_defaults_but_keeps_tray_choice(tmp_path):
    legacy = default_preferences()
    legacy["layout_schema"] = 2
    legacy["tray_indicator"] = False
    legacy["panels"]["history"]["height"] = 4
    save_preferences(tmp_path, legacy)
    loaded = load_preferences(tmp_path)
    assert loaded["layout_schema"] == 3
    assert loaded["tray_indicator"] is False
    assert loaded["panels"]["history"]["height"] == 1


def test_legacy_preferences_keep_unrelated_tray_choice(tmp_path):
    save_preferences(tmp_path, {"tray_indicator": False, "panels": {}})
    assert load_preferences(tmp_path)["tray_indicator"] is False
    assert load_preferences(tmp_path)["layout_schema"] == 3

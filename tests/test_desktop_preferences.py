import json

from app.desktop_preferences import (
    LAYOUT_SCHEMA,
    PANEL_IDS,
    default_preferences,
    load_preferences,
    preferences_path,
    save_preferences,
    show_all_panels,
)


def test_default_preferences_show_every_stable_panel_and_enable_tray_indicator():
    preferences = default_preferences()

    assert preferences["layout_schema"] == LAYOUT_SCHEMA == 4
    assert preferences["tray_indicator"] is True
    assert tuple(preferences["panels"]) == PANEL_IDS
    assert all(preferences["panels"].values())


def test_preferences_round_trip_and_preserve_hidden_panel(tmp_path):
    preferences = default_preferences()
    preferences["tray_indicator"] = False
    preferences["panels"]["history"] = False

    save_preferences(tmp_path, preferences)
    loaded = load_preferences(tmp_path)

    assert loaded["tray_indicator"] is False
    assert loaded["panels"]["history"] is False


def test_show_all_panels_restores_visibility_without_changing_tray_choice():
    preferences = default_preferences()
    preferences["tray_indicator"] = False
    preferences["panels"]["weekly"] = False
    preferences["panels"]["history"] = False

    restored = show_all_panels(preferences)

    assert restored["tray_indicator"] is False
    assert all(restored["panels"].values())


def test_corrupt_preferences_fall_back_to_defaults(tmp_path):
    preferences_path(tmp_path).write_text("{not json", encoding="utf-8")

    assert load_preferences(tmp_path) == default_preferences()


def test_current_schema_ignores_geometry_and_unknown_panels(tmp_path):
    raw = {
        "layout_schema": LAYOUT_SCHEMA,
        "tray_indicator": True,
        "panels": {
            "five-hour": {"visible": False, "column": 4, "width": 4},
            "weekly": False,
            "made-up": False,
        },
    }
    preferences_path(tmp_path).write_text(json.dumps(raw), encoding="utf-8")

    loaded = load_preferences(tmp_path)

    assert loaded["panels"]["five-hour"] is True
    assert loaded["panels"]["weekly"] is False
    assert "made-up" not in loaded["panels"]
    assert set(loaded) == {"layout_schema", "tray_indicator", "panels"}
    assert json.loads(preferences_path(tmp_path).read_text(encoding="utf-8")) == loaded


def test_v2_layout_migrates_to_all_visible_and_preserves_tray_choice(tmp_path):
    legacy = {
        "layout_schema": 2,
        "tray_indicator": False,
        "panels": {
            "history": {
                "visible": False,
                "column": 1,
                "row": 3,
                "width": 4,
                "height": 4,
            },
        },
    }
    preferences_path(tmp_path).write_text(json.dumps(legacy), encoding="utf-8")

    loaded = load_preferences(tmp_path)

    assert loaded["layout_schema"] == LAYOUT_SCHEMA
    assert loaded["tray_indicator"] is False
    assert all(loaded["panels"].values())
    assert json.loads(preferences_path(tmp_path).read_text(encoding="utf-8")) == loaded


def test_v3_layout_migrates_to_all_visible_and_discards_geometry(tmp_path):
    legacy = {
        "layout_schema": 3,
        "tray_indicator": False,
        "panels": {
            panel_id: {
                "visible": panel_id != "account",
                "column": 1,
                "row": 20,
                "width": 4,
                "height": 4,
            }
            for panel_id in PANEL_IDS
        },
    }
    preferences_path(tmp_path).write_text(json.dumps(legacy), encoding="utf-8")

    loaded = load_preferences(tmp_path)

    assert loaded == {
        "layout_schema": LAYOUT_SCHEMA,
        "tray_indicator": False,
        "panels": {panel_id: True for panel_id in PANEL_IDS},
    }
    assert json.loads(preferences_path(tmp_path).read_text(encoding="utf-8")) == loaded

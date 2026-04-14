from src.window_info import get_active_window


def test_get_active_window_uses_quartz_fallback(monkeypatch):
    monkeypatch.setattr(
        "src.window_info.get_frontmost_window_via_quartz",
        lambda: {
            "window_id": 123,
            "app_name": "Cursor",
            "window_title": "main.py",
            "bounds": {"x": 1, "y": 2, "width": 3, "height": 4},
        },
    )
    monkeypatch.setattr("src.window_info.get_active_app_name", lambda: "")
    monkeypatch.setattr("src.window_info.get_window_title", lambda: "")

    window = get_active_window(include_bounds=False)

    assert window.app_name == "Cursor"
    assert window.window_title == "main.py"
    assert window.window_id is None
    assert window.window_bounds is None


def test_get_active_window_prefers_applescript_and_keeps_bounds(monkeypatch):
    monkeypatch.setattr(
        "src.window_info.get_frontmost_window_via_quartz",
        lambda: {
            "window_id": 456,
            "app_name": "QuartzApp",
            "window_title": "QuartzTitle",
            "bounds": {"x": 10, "y": 20, "width": 30, "height": 40},
        },
    )
    monkeypatch.setattr("src.window_info.get_active_app_name", lambda: "Comet")
    monkeypatch.setattr("src.window_info.get_window_title", lambda: "Chat")

    window = get_active_window(include_bounds=True)

    assert window.app_name == "Comet"
    assert window.window_title == "Chat"
    assert window.window_id == 456
    assert window.window_bounds == {"x": 10, "y": 20, "width": 30, "height": 40}

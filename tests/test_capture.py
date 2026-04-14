from types import SimpleNamespace

import src.capture as capture_module


def test_permission_related_capture_error_detects_permission_words():
    assert capture_module.is_permission_related_capture_error("permission denied")
    assert capture_module.is_permission_related_capture_error("not allowed")


def test_permission_related_capture_error_detects_display_creation_failure():
    assert capture_module.is_permission_related_capture_error("could not create image from display")


def test_permission_related_capture_error_ignores_unrelated_errors():
    assert not capture_module.is_permission_related_capture_error("timed out while writing file")


def test_has_screen_recording_permission_returns_none_without_quartz(monkeypatch):
    monkeypatch.setattr(capture_module, "Quartz", None)
    assert capture_module.has_screen_recording_permission() is None


def test_request_screen_recording_permission_opens_settings_on_denial(monkeypatch):
    opened = {"value": False}

    monkeypatch.setattr(
        capture_module,
        "Quartz",
        SimpleNamespace(
            CGPreflightScreenCaptureAccess=lambda: False,
            CGRequestScreenCaptureAccess=lambda: False,
        ),
    )
    monkeypatch.setattr(
        capture_module,
        "open_screen_recording_settings",
        lambda: opened.__setitem__("value", True) or True,
    )

    assert capture_module.request_screen_recording_permission() is False
    assert opened["value"] is True


def test_request_screen_recording_permission_returns_true_when_already_granted(monkeypatch):
    monkeypatch.setattr(
        capture_module,
        "Quartz",
        SimpleNamespace(CGPreflightScreenCaptureAccess=lambda: True),
    )

    assert capture_module.request_screen_recording_permission() is True

from pathlib import Path

import run_snaplog_app


def test_ensure_user_config_copies_settings_yaml(tmp_path, monkeypatch):
    resources_dir = tmp_path / "Resources"
    config_dir = resources_dir / "config"
    config_dir.mkdir(parents=True)
    bundled_config = config_dir / "settings.yaml"
    bundled_config.write_text("logging:\n  level: INFO\n", encoding="utf-8")

    app_support_dir = tmp_path / "Application Support" / "SnapLog"
    monkeypatch.setattr(run_snaplog_app, "APP_SUPPORT_DIR", app_support_dir)

    user_config_path = run_snaplog_app.ensure_user_config(resources_dir)

    assert user_config_path == app_support_dir / "settings.yaml"
    assert user_config_path.read_text(encoding="utf-8") == bundled_config.read_text(encoding="utf-8")


def test_ensure_user_config_falls_back_to_example(tmp_path, monkeypatch):
    resources_dir = tmp_path / "Resources"
    config_dir = resources_dir / "config"
    config_dir.mkdir(parents=True)
    bundled_example = config_dir / "settings.yaml.example"
    bundled_example.write_text("capture:\n  interval: 60\n", encoding="utf-8")

    app_support_dir = tmp_path / "Application Support" / "SnapLog"
    monkeypatch.setattr(run_snaplog_app, "APP_SUPPORT_DIR", app_support_dir)

    user_config_path = run_snaplog_app.ensure_user_config(resources_dir)

    assert user_config_path == app_support_dir / "settings.yaml"
    assert user_config_path.read_text(encoding="utf-8") == bundled_example.read_text(encoding="utf-8")


def test_ensure_user_config_keeps_existing_user_file(tmp_path, monkeypatch):
    resources_dir = tmp_path / "Resources"
    config_dir = resources_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.yaml").write_text("storage:\n  retention_days: 14\n", encoding="utf-8")

    app_support_dir = tmp_path / "Application Support" / "SnapLog"
    app_support_dir.mkdir(parents=True)
    existing_config = app_support_dir / "settings.yaml"
    existing_config.write_text("storage:\n  retention_days: 30\n", encoding="utf-8")
    monkeypatch.setattr(run_snaplog_app, "APP_SUPPORT_DIR", app_support_dir)

    user_config_path = run_snaplog_app.ensure_user_config(resources_dir)

    assert user_config_path == existing_config
    assert user_config_path.read_text(encoding="utf-8") == "storage:\n  retention_days: 30\n"

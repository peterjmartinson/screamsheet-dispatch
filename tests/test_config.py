"""Unit tests for screamsheet_dispatch.config (load_dispatch_config)."""
import os
from pathlib import Path

import pytest
import yaml

from screamsheet_dispatch.config import (
    DispatchConfig,
    SmtpConfig,
    load_dispatch_config,
)


# ---------------------------------------------------------------------------
# load_dispatch_config — happy path
# ---------------------------------------------------------------------------

class TestLoadDispatchConfig:
    def test_returns_dispatch_config(self, minimal_config_file):
        cfg = load_dispatch_config(minimal_config_file)
        assert isinstance(cfg, DispatchConfig)

    def test_smtp_host_from_env(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.host == "smtp.example.com"

    def test_smtp_user_from_env(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.user == "user@example.com"

    def test_smtp_password_from_env(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.password == "secret"

    def test_smtp_port_from_yaml(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.port == 465

    def test_smtp_from_address_from_yaml(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.from_address == "sender@example.com"

    def test_smtp_send_delay_from_yaml(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.smtp.send_delay_seconds == 0.0

    def test_admin_email_parsed(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.admin.alert_email == "admin@example.com"

    def test_google_sheets_spreadsheet_id_parsed(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.google_sheets.spreadsheet_id == "SHEET_ID"

    def test_paths_config_store_parsed(self, minimal_config_file, smtp_env, tmp_path):
        cfg = load_dispatch_config(minimal_config_file)
        assert "configs" in cfg.paths.config_store

    def test_retention_outbox_days_parsed(self, minimal_config_file, smtp_env):
        cfg = load_dispatch_config(minimal_config_file)
        assert cfg.retention.outbox_days == 7


# ---------------------------------------------------------------------------
# load_dispatch_config — error cases
# ---------------------------------------------------------------------------

class TestLoadDispatchConfigErrors:
    def test_raises_file_not_found_for_missing_file(self, tmp_path, smtp_env):
        with pytest.raises(FileNotFoundError):
            load_dispatch_config(tmp_path / "nonexistent.yaml")

    def test_raises_environment_error_for_missing_smtp_host(self, tmp_path):
        cfg_path = tmp_path / "dispatch_config.yaml"
        cfg_path.write_text(yaml.dump({"smtp": {}}), encoding="utf-8")
        # No env vars set
        with pytest.raises(EnvironmentError, match="DISPATCH_SMTP_HOST"):
            load_dispatch_config(cfg_path)

    def test_raises_environment_error_for_missing_smtp_user(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DISPATCH_SMTP_HOST", "smtp.example.com")
        cfg_path = tmp_path / "dispatch_config.yaml"
        cfg_path.write_text(yaml.dump({"smtp": {}}), encoding="utf-8")
        with pytest.raises(EnvironmentError, match="DISPATCH_SMTP_USER"):
            load_dispatch_config(cfg_path)

    def test_raises_environment_error_for_missing_smtp_password(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DISPATCH_SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("DISPATCH_SMTP_USER", "user@example.com")
        cfg_path = tmp_path / "dispatch_config.yaml"
        cfg_path.write_text(yaml.dump({"smtp": {}}), encoding="utf-8")
        with pytest.raises(EnvironmentError, match="DISPATCH_SMTP_PASSWORD"):
            load_dispatch_config(cfg_path)

    def test_missing_file_error_mentions_example(self, tmp_path, smtp_env):
        with pytest.raises(FileNotFoundError, match="example"):
            load_dispatch_config(tmp_path / "nonexistent.yaml")

"""Shared test fixtures for the screamsheet-dispatch test suite."""
import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def smtp_env(monkeypatch):
    """Set the three required SMTP environment variables."""
    monkeypatch.setenv("DISPATCH_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("DISPATCH_SMTP_USER", "user@example.com")
    monkeypatch.setenv("DISPATCH_SMTP_PASSWORD", "secret")


@pytest.fixture
def minimal_config_file(tmp_path, smtp_env):
    """Write a minimal dispatch_config.yaml and return its Path."""
    cfg = {
        "smtp": {"port": 465, "from_address": "sender@example.com", "send_delay_seconds": 0.0},
        "admin": {"alert_email": "admin@example.com"},
        "google_sheets": {
            "spreadsheet_id": "SHEET_ID",
            "credentials_file": "/path/to/creds.json",
        },
        "paths": {"config_store": str(tmp_path / "configs"), "outbox": str(tmp_path / "outbox")},
        "retention": {"outbox_days": 7},
    }
    config_path = tmp_path / "dispatch_config.yaml"
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return config_path

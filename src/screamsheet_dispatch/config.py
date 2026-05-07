"""Load and expose dispatch configuration from dispatch_config.yaml and environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SmtpConfig:
    """SMTP connection settings.  Host, user, and password come from env vars."""
    host: str
    port: int
    from_address: str
    user: str
    password: str
    send_delay_seconds: float = 2.0


@dataclass
class AdminConfig:
    """Admin alert address for end-of-run summaries."""
    alert_email: str


@dataclass
class GoogleSheetsConfig:
    """Google Sheets API connection settings."""
    spreadsheet_id: str
    credentials_file: str


@dataclass
class PathsConfig:
    """Filesystem paths used by the dispatcher."""
    config_store: str
    outbox: str


@dataclass
class RetentionConfig:
    """How long to keep generated output before cleanup."""
    outbox_days: int = 7


@dataclass
class DispatchConfig:
    """Top-level dispatch configuration."""
    smtp: SmtpConfig
    admin: AdminConfig
    google_sheets: GoogleSheetsConfig
    paths: PathsConfig
    retention: RetentionConfig


def _require_env(name: str) -> str:
    """Return the value of a required environment variable.

    Raises:
        EnvironmentError: if the variable is not set or is empty.
    """
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable not set: {name}")
    return value


def load_dispatch_config(path: Path) -> DispatchConfig:
    """Load dispatch_config.yaml and merge SMTP credentials from environment variables.

    Args:
        path: Path to dispatch_config.yaml.

    Raises:
        FileNotFoundError: if the config file does not exist.
        EnvironmentError: if any required SMTP env var is missing.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Dispatch config not found: {path}\n"
            "Copy dispatch_config.yaml.example to dispatch_config.yaml and fill in your values."
        )

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    smtp_raw = raw.get("smtp", {})
    smtp = SmtpConfig(
        host=_require_env("DISPATCH_SMTP_HOST"),
        port=int(smtp_raw.get("port", 465)),
        from_address=str(smtp_raw.get("from_address", "")),
        user=_require_env("DISPATCH_SMTP_USER"),
        password=_require_env("DISPATCH_SMTP_PASSWORD"),
        send_delay_seconds=float(smtp_raw.get("send_delay_seconds", 2.0)),
    )

    admin_raw = raw.get("admin", {})
    admin = AdminConfig(alert_email=str(admin_raw.get("alert_email", "")))

    sheets_raw = raw.get("google_sheets", {})
    google_sheets = GoogleSheetsConfig(
        spreadsheet_id=str(sheets_raw.get("spreadsheet_id", "")),
        credentials_file=str(sheets_raw.get("credentials_file", "")),
    )

    paths_raw = raw.get("paths", {})
    paths = PathsConfig(
        config_store=str(paths_raw.get("config_store", "")),
        outbox=str(paths_raw.get("outbox", "")),
    )

    retention_raw = raw.get("retention", {})
    retention = RetentionConfig(
        outbox_days=int(retention_raw.get("outbox_days", 7)),
    )

    return DispatchConfig(
        smtp=smtp,
        admin=admin,
        google_sheets=google_sheets,
        paths=paths,
        retention=retention,
    )

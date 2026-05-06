"""Unit tests for screamsheet_dispatch.sync."""
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

from screamsheet_dispatch.sync import (
    SyncResult,
    _parse_sheet_list,
    remove_stale_configs,
    sync_subscribers,
    write_subscriber_config,
)


# ---------------------------------------------------------------------------
# write_subscriber_config
# ---------------------------------------------------------------------------

class TestWriteSubscriberConfig:
    def test_creates_yaml_file(self, tmp_path):
        write_subscriber_config("abc-123", {"name": "Alice"}, tmp_path)
        assert (tmp_path / "abc-123.yaml").exists()

    def test_file_contains_expected_data(self, tmp_path):
        write_subscriber_config("abc-123", {"email": "a@b.com"}, tmp_path)
        content = yaml.safe_load((tmp_path / "abc-123.yaml").read_text())
        assert content["email"] == "a@b.com"

    def test_creates_config_store_directory_if_missing(self, tmp_path):
        new_dir = tmp_path / "sub" / "configs"
        write_subscriber_config("g1", {"name": "Bob"}, new_dir)
        assert new_dir.is_dir()


# ---------------------------------------------------------------------------
# remove_stale_configs
# ---------------------------------------------------------------------------

class TestRemoveStaleConfigs:
    def test_removes_file_not_in_current_guids(self, tmp_path):
        (tmp_path / "old-guid.yaml").write_text("name: old", encoding="utf-8")
        remove_stale_configs(set(), tmp_path)
        assert not (tmp_path / "old-guid.yaml").exists()

    def test_keeps_file_in_current_guids(self, tmp_path):
        (tmp_path / "current.yaml").write_text("name: keep", encoding="utf-8")
        remove_stale_configs({"current"}, tmp_path)
        assert (tmp_path / "current.yaml").exists()

    def test_returns_count_of_removed_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("x: 1", encoding="utf-8")
        (tmp_path / "b.yaml").write_text("x: 2", encoding="utf-8")
        count = remove_stale_configs({"a"}, tmp_path)
        assert count == 1

    def test_returns_zero_when_nothing_removed(self, tmp_path):
        (tmp_path / "keep.yaml").write_text("x: 1", encoding="utf-8")
        count = remove_stale_configs({"keep"}, tmp_path)
        assert count == 0


# ---------------------------------------------------------------------------
# _parse_sheet_list
# ---------------------------------------------------------------------------

class TestParseSheetList:
    def test_parses_comma_separated_sheet_types(self):
        row = {"sheets": "nhl, mlb, nba"}
        result = _parse_sheet_list(row)
        assert result == ["nhl", "mlb", "nba"]

    def test_returns_empty_list_for_blank_sheets(self):
        row = {"sheets": ""}
        result = _parse_sheet_list(row)
        assert result == []

    def test_returns_empty_list_when_key_absent(self):
        result = _parse_sheet_list({})
        assert result == []


# ---------------------------------------------------------------------------
# sync_subscribers — fallback on API failure
# ---------------------------------------------------------------------------

class TestSyncSubscribersFallback:
    def test_returns_used_fallback_true_on_api_error(self, minimal_config_file, smtp_env):
        from screamsheet_dispatch.config import load_dispatch_config
        config = load_dispatch_config(minimal_config_file)

        with patch(
            "screamsheet_dispatch.sync.Credentials.from_service_account_file",
            side_effect=Exception("API down"),
        ):
            result = sync_subscribers(config)

        assert result.used_fallback is True

    def test_returns_success_false_on_api_error(self, minimal_config_file, smtp_env):
        from screamsheet_dispatch.config import load_dispatch_config
        config = load_dispatch_config(minimal_config_file)

        with patch(
            "screamsheet_dispatch.sync.Credentials.from_service_account_file",
            side_effect=Exception("API down"),
        ):
            result = sync_subscribers(config)

        assert result.success is False

    def test_error_field_populated_on_api_failure(self, minimal_config_file, smtp_env):
        from screamsheet_dispatch.config import load_dispatch_config
        config = load_dispatch_config(minimal_config_file)

        with patch(
            "screamsheet_dispatch.sync.Credentials.from_service_account_file",
            side_effect=Exception("timeout"),
        ):
            result = sync_subscribers(config)

        assert result.error is not None
        assert "timeout" in result.error


# ---------------------------------------------------------------------------
# sync_subscribers — happy path (git commit)
# ---------------------------------------------------------------------------

class TestSyncSubscribersSuccess:
    def _make_config(self, minimal_config_file, smtp_env):
        from screamsheet_dispatch.config import load_dispatch_config
        return load_dispatch_config(minimal_config_file)

    def test_calls_git_commit_after_writing_configs(self, minimal_config_file, smtp_env, tmp_path):
        config = self._make_config(minimal_config_file, smtp_env)
        rows = [{"guid": "g1", "name": "Alice", "email": "a@b.com", "sheets": "nhl"}]

        mock_gc = MagicMock()
        mock_gc.open_by_key.return_value.sheet1.get_all_records.return_value = rows

        with patch("screamsheet_dispatch.sync.Credentials.from_service_account_file"), \
             patch("screamsheet_dispatch.sync.gspread.authorize", return_value=mock_gc), \
             patch("screamsheet_dispatch.sync._git_commit_push") as mock_git:
            result = sync_subscribers(config)

        mock_git.assert_called_once()

    def test_writes_one_config_file_per_subscriber(self, minimal_config_file, smtp_env, tmp_path):
        config = self._make_config(minimal_config_file, smtp_env)
        rows = [
            {"guid": "g1", "name": "Alice", "email": "a@b.com", "sheets": "nhl"},
            {"guid": "g2", "name": "Bob", "email": "b@b.com", "sheets": "mlb"},
        ]
        mock_gc = MagicMock()
        mock_gc.open_by_key.return_value.sheet1.get_all_records.return_value = rows

        with patch("screamsheet_dispatch.sync.Credentials.from_service_account_file"), \
             patch("screamsheet_dispatch.sync.gspread.authorize", return_value=mock_gc), \
             patch("screamsheet_dispatch.sync._git_commit_push"):
            result = sync_subscribers(config)

        config_store = Path(config.paths.config_store)
        assert (config_store / "g1.yaml").exists()
        assert (config_store / "g2.yaml").exists()

    def test_returns_subscribers_updated_count(self, minimal_config_file, smtp_env):
        config = self._make_config(minimal_config_file, smtp_env)
        rows = [{"guid": "g1", "name": "Alice", "email": "a@b.com", "sheets": "nhl"}]
        mock_gc = MagicMock()
        mock_gc.open_by_key.return_value.sheet1.get_all_records.return_value = rows

        with patch("screamsheet_dispatch.sync.Credentials.from_service_account_file"), \
             patch("screamsheet_dispatch.sync.gspread.authorize", return_value=mock_gc), \
             patch("screamsheet_dispatch.sync._git_commit_push"):
            result = sync_subscribers(config)

        assert result.subscribers_updated == 1

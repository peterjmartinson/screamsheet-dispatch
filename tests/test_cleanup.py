"""Unit tests for screamsheet_dispatch.cleanup."""
from datetime import date, timedelta
from pathlib import Path

import pytest

from screamsheet_dispatch.cleanup import cleanup_outbox


def _make_dated_folder(outbox: Path, days_ago: int) -> Path:
    """Create a YYYYMMDD-named folder `days_ago` days before today."""
    folder_date = date.today() - timedelta(days=days_ago)
    folder = outbox / folder_date.strftime("%Y%m%d")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------------------
# cleanup_outbox
# ---------------------------------------------------------------------------

class TestCleanupOutbox:
    def test_removes_folder_older_than_retention(self, tmp_path):
        old_folder = _make_dated_folder(tmp_path, days_ago=10)
        cleanup_outbox(tmp_path, retention_days=7)
        assert not old_folder.exists()

    def test_keeps_folder_within_retention(self, tmp_path):
        recent_folder = _make_dated_folder(tmp_path, days_ago=3)
        cleanup_outbox(tmp_path, retention_days=7)
        assert recent_folder.exists()

    def test_returns_count_of_deleted_folders(self, tmp_path):
        _make_dated_folder(tmp_path, days_ago=10)
        _make_dated_folder(tmp_path, days_ago=12)
        count = cleanup_outbox(tmp_path, retention_days=7)
        assert count == 2

    def test_returns_zero_when_nothing_to_delete(self, tmp_path):
        _make_dated_folder(tmp_path, days_ago=2)
        count = cleanup_outbox(tmp_path, retention_days=7)
        assert count == 0

    def test_returns_zero_when_outbox_does_not_exist(self, tmp_path):
        count = cleanup_outbox(tmp_path / "nonexistent", retention_days=7)
        assert count == 0

    def test_skips_non_date_named_folders(self, tmp_path):
        weird_folder = tmp_path / "not-a-date"
        weird_folder.mkdir()
        cleanup_outbox(tmp_path, retention_days=7)
        assert weird_folder.exists()

    def test_keeps_folder_exactly_at_retention_boundary(self, tmp_path):
        boundary_folder = _make_dated_folder(tmp_path, days_ago=7)
        cleanup_outbox(tmp_path, retention_days=7)
        assert boundary_folder.exists()

"""Unit tests for screamsheet_dispatch.runner."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from screamsheet_dispatch.runner import run_for_subscriber


# ---------------------------------------------------------------------------
# run_for_subscriber
# ---------------------------------------------------------------------------

class TestRunForSubscriber:
    def _fake_result(self):
        return [
            {
                "pdf_path": "/tmp/nhl_20260506.pdf",
                "sheet_type": "nhl",
                "layout_clean": True,
                "issues": [],
            }
        ]

    def test_returns_parsed_json_on_success(self, tmp_path):
        expected = self._fake_result()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected)

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result):
            result = run_for_subscriber("g1", tmp_path / "g1.yaml", tmp_path / "out")

        assert result == expected

    def test_returns_empty_list_on_non_zero_exit(self, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "generator crashed"
        mock_result.stdout = ""

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result):
            result = run_for_subscriber("g1", tmp_path / "g1.yaml", tmp_path / "out")

        assert result == []

    def test_returns_empty_list_on_invalid_json(self, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json {"

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result):
            result = run_for_subscriber("g1", tmp_path / "g1.yaml", tmp_path / "out")

        assert result == []

    def test_invokes_uv_run_screamsheet_service(self, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result) as mock_run:
            run_for_subscriber("g1", tmp_path / "g1.yaml", tmp_path / "out")

        call_args = mock_run.call_args[0][0]
        assert "uv" in call_args
        assert "screamsheet-service" in call_args

    def test_passes_config_path_to_generator(self, tmp_path):
        config_path = tmp_path / "g1.yaml"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result) as mock_run:
            run_for_subscriber("g1", config_path, tmp_path / "out")

        call_args = mock_run.call_args[0][0]
        assert str(config_path) in call_args

    def test_creates_output_dir_if_missing(self, tmp_path):
        output_dir = tmp_path / "outbox" / "20260506" / "g1"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch("screamsheet_dispatch.runner.subprocess.run", return_value=mock_result):
            run_for_subscriber("g1", tmp_path / "g1.yaml", output_dir)

        assert output_dir.is_dir()

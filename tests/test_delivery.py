"""Unit tests for screamsheet_dispatch.delivery."""
import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from screamsheet_dispatch.config import SmtpConfig
from screamsheet_dispatch.delivery import send_admin_alert, send_subscriber_email


@pytest.fixture
def smtp_config():
    return SmtpConfig(
        host="smtp.example.com",
        port=465,
        from_address="sender@example.com",
        user="user@example.com",
        password="secret",
        send_delay_seconds=0.0,
    )


# ---------------------------------------------------------------------------
# send_subscriber_email
# ---------------------------------------------------------------------------

class TestSendSubscriberEmail:
    def test_connects_with_smtp_ssl(self, smtp_config, tmp_path):
        pdf = tmp_path / "nhl_20260506.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_subscriber_email("a@b.com", [pdf], "May 06, 2026", smtp_config)

        MockSSL.assert_called_once_with("smtp.example.com", 465)

    def test_logs_in_with_credentials(self, smtp_config, tmp_path):
        pdf = tmp_path / "nhl.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_subscriber_email("a@b.com", [pdf], "May 06, 2026", smtp_config)

        mock_server.login.assert_called_once_with("user@example.com", "secret")

    def test_sends_to_recipient(self, smtp_config, tmp_path):
        pdf = tmp_path / "nhl.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_subscriber_email("subscriber@example.com", [pdf], "May 06, 2026", smtp_config)

        args = mock_server.sendmail.call_args[0]
        assert args[1] == "subscriber@example.com"

    def test_subject_contains_date(self, smtp_config, tmp_path):
        pdf = tmp_path / "nhl.pdf"
        pdf.write_bytes(b"%PDF-fake")

        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_subscriber_email("a@b.com", [pdf], "May 06, 2026", smtp_config)

        message_str = mock_server.sendmail.call_args[0][2]
        assert "May 06, 2026" in message_str


# ---------------------------------------------------------------------------
# send_admin_alert
# ---------------------------------------------------------------------------

class TestSendAdminAlert:
    def test_sends_to_admin_email(self, smtp_config):
        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_admin_alert("Run complete.", smtp_config, "admin@example.com")

        args = mock_server.sendmail.call_args[0]
        assert args[1] == "admin@example.com"

    def test_body_appears_in_message(self, smtp_config):
        with patch("screamsheet_dispatch.delivery.smtplib.SMTP_SSL") as MockSSL:
            mock_server = MagicMock()
            MockSSL.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockSSL.return_value.__exit__ = MagicMock(return_value=False)
            send_admin_alert("Run complete.", smtp_config, "admin@example.com")

        message_str = mock_server.sendmail.call_args[0][2]
        assert "Run complete." in message_str

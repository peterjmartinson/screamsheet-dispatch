"""Email delivery for subscriber PDFs via Hostinger SMTP."""
from __future__ import annotations

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List

from .config import SmtpConfig

logger = logging.getLogger(__name__)


def send_subscriber_email(
    email_to: str,
    pdf_paths: List[Path],
    date_str: str,
    smtp_config: SmtpConfig,
) -> None:
    """Send one email to a subscriber with all their PDFs as attachments.

    Args:
        email_to:    Recipient address.
        pdf_paths:   Paths to the generated PDF files.
        date_str:    Human-readable date string for the subject/body.
        smtp_config: SMTP connection and credential settings.

    Raises:
        smtplib.SMTPException: on any SMTP-level failure.
    """
    msg = MIMEMultipart()
    msg["From"] = smtp_config.from_address
    msg["To"] = email_to
    msg["Subject"] = f"Scream Sheet for {date_str}"

    sheet_names = ", ".join(p.stem for p in pdf_paths)
    body = (
        f"Good morning!\n\n"
        f"Your scream sheets for {date_str} are attached:\n"
        f"  {sheet_names}\n\n"
        f"— Scream Sheet Dispatcher"
    )
    msg.attach(MIMEText(body, "plain"))

    for pdf_path in pdf_paths:
        with open(pdf_path, "rb") as fh:
            part = MIMEApplication(fh.read(), Name=pdf_path.name)
        part["Content-Disposition"] = f'attachment; filename="{pdf_path.name}"'
        msg.attach(part)

    with smtplib.SMTP_SSL(smtp_config.host, smtp_config.port) as server:
        server.login(smtp_config.user, smtp_config.password)
        server.sendmail(smtp_config.from_address, email_to, msg.as_string())


def send_admin_alert(
    body: str,
    smtp_config: SmtpConfig,
    admin_email: str,
) -> None:
    """Send the run summary to the admin email address as the message body.

    Args:
        body:        Plain-text run log content.
        smtp_config: SMTP connection and credential settings.
        admin_email: Destination address.

    Raises:
        smtplib.SMTPException: on any SMTP-level failure.
    """
    msg = MIMEMultipart()
    msg["From"] = smtp_config.from_address
    msg["To"] = admin_email
    msg["Subject"] = "Scream Sheet Dispatch Run Summary"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL(smtp_config.host, smtp_config.port) as server:
        server.login(smtp_config.user, smtp_config.password)
        server.sendmail(smtp_config.from_address, admin_email, msg.as_string())

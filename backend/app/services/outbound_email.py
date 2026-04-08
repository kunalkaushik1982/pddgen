r"""
Purpose: SMTP delivery for transactional auth emails (verification + password reset).
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\outbound_email.py
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host.strip())


def send_html_email(
    *,
    settings: Settings,
    to_addr: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    """Send one HTML (+ plain text fallback) email via SMTP."""
    if not smtp_configured(settings):
        raise RuntimeError("SMTP is not configured (smtp_host is empty).")
    from_addr = settings.smtp_from_email.strip() or settings.smtp_user.strip()
    if not from_addr:
        raise RuntimeError("Configure smtp_from_email or smtp_user for outbound mail.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host.strip(), settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        user = settings.smtp_user.strip()
        password = settings.smtp_password.strip()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)

    logger.info("Outbound email sent", extra={"to": to_addr, "subject": subject})


def send_email_verification_message(
    *,
    settings: Settings,
    to_email: str,
    verify_url: str,
    app_name: str,
) -> None:
    subject = f"Verify your email for {app_name}"
    text_body = (
        f"Open this link to verify your email address:\n{verify_url}\n\n"
        f"If you did not create an account, ignore this message."
    )
    html_body = f"""<!DOCTYPE html>
<html><body>
<p>Verify your email for <strong>{app_name}</strong>.</p>
<p><a href="{verify_url}">Verify email</a></p>
<p style="color:#666;font-size:12px">If you did not create an account, ignore this message.</p>
</body></html>"""
    send_html_email(
        settings=settings,
        to_addr=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_password_reset_message(
    *,
    settings: Settings,
    to_email: str,
    reset_url: str,
    app_name: str,
) -> None:
    subject = f"Reset your password for {app_name}"
    text_body = (
        f"Open this link to choose a new password:\n{reset_url}\n\n"
        f"If you did not request a reset, ignore this message."
    )
    html_body = f"""<!DOCTYPE html>
<html><body>
<p>Reset your password for <strong>{app_name}</strong>.</p>
<p><a href="{reset_url}">Reset password</a></p>
<p style="color:#666;font-size:12px">If you did not request a reset, ignore this message.</p>
</body></html>"""
    send_html_email(
        settings=settings,
        to_addr=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

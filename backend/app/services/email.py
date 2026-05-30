"""
Transactional email via Resend (https://resend.com).

Degrades gracefully: if RESEND_API_KEY is unset, emails are logged instead of
sent — so local development and registration still work without a key.
"""
import os
import logging

import httpx

logger = logging.getLogger("touse.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
# Resend's shared sandbox sender works without domain verification.
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Touse <onboarding@resend.dev>")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True on success, False if skipped or failed."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s (%r)", to, subject)
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html},
            )
            resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 — email must never break the caller
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


async def send_password_reset_email(to: str, first_name: str, token: str) -> bool:
    """Send a password-reset link. Token expires in 1 hour (see security.py)."""
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
      <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;color:#1d1d1d">
        <h2 style="color:#1C3A2F">Reset your Touse password</h2>
        <p>Hi {first_name}, we got a request to reset the password on your account.
           Click the button below to choose a new one. If you didn't ask for this,
           you can safely ignore this email.</p>
        <p style="margin:28px 0">
          <a href="{link}"
             style="background:#1C3A2F;color:#fff;padding:12px 24px;border-radius:4px;
                    text-decoration:none;font-weight:600">
            Reset password
          </a>
        </p>
        <p style="color:#666;font-size:13px">
          Or paste this link into your browser:<br>
          <a href="{link}" style="color:#1C3A2F">{link}</a>
        </p>
        <p style="color:#999;font-size:12px">This link expires in 1 hour.</p>
      </div>
    """
    return await send_email(to, "Reset your Touse password", html)


async def send_verification_email(to: str, first_name: str, token: str) -> bool:
    """Send the account email-verification link."""
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
      <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;color:#1d1d1d">
        <h2 style="color:#1C3A2F">Welcome to Touse, {first_name}!</h2>
        <p>Confirm your email address to finish setting up your account.</p>
        <p style="margin:28px 0">
          <a href="{link}"
             style="background:#1C3A2F;color:#fff;padding:12px 24px;border-radius:4px;
                    text-decoration:none;font-weight:600">
            Verify my email
          </a>
        </p>
        <p style="color:#666;font-size:13px">
          Or paste this link into your browser:<br>
          <a href="{link}" style="color:#1C3A2F">{link}</a>
        </p>
        <p style="color:#999;font-size:12px">This link expires in 3 days.</p>
      </div>
    """
    return await send_email(to, "Verify your Touse account", html)

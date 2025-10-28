import smtplib
from email.message import EmailMessage
from typing import Optional
import logging

from ..core.config import settings


def can_send_email() -> bool:
    """Check if email can be sent using either SMTP or Mailjet"""
    smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_SENDER)
    mailjet_configured = bool(
        hasattr(settings, 'MAILJET_API_KEY') and 
        hasattr(settings, 'MAILJET_SECRET_KEY') and 
        hasattr(settings, 'MAILJET_SENDER') and
        settings.MAILJET_API_KEY and 
        settings.MAILJET_SECRET_KEY and 
        settings.MAILJET_SENDER
    )
    return smtp_configured or mailjet_configured


def send_email_smtp(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> None:
    """Send email using SMTP"""
    if not settings.SMTP_HOST or not settings.SMTP_SENDER:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_SENDER
    msg["To"] = to_email
    if body_html:
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text)

    try:
        if settings.SMTP_USE_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        logging.info(f"Email sent successfully to {to_email} via SMTP")
    except Exception as e:
        logging.error(f"Failed to send email via SMTP: {str(e)}")


def send_email_mailjet(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> None:
    """Send email using Mailjet API"""
    try:
        from mailjet_rest import Client
    except ImportError:
        logging.error("Mailjet library not installed. Install with: pip install mailjet-rest")
        return

    if not (hasattr(settings, 'MAILJET_API_KEY') and 
            hasattr(settings, 'MAILJET_SECRET_KEY') and 
            hasattr(settings, 'MAILJET_SENDER') and
            settings.MAILJET_API_KEY and 
            settings.MAILJET_SECRET_KEY and 
            settings.MAILJET_SENDER):
        return

    mailjet = Client(auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY), version='v3.1')

    sender_name = getattr(settings, 'MAILJET_SENDER_NAME', None) or "Nexia Fitness"
    sender_email = settings.MAILJET_SENDER

    data = {
        'Messages': [
            {
                "From": {
                    "Email": sender_email,
                    "Name": sender_name
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": to_email.split('@')[0]  # Use email prefix as name
                    }
                ],
                "Subject": subject,
                "TextPart": body_text,
            }
        ]
    }

    # Add HTML part if provided
    if body_html:
        data['Messages'][0]['HTMLPart'] = body_html

    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            logging.info(f"Email sent successfully to {to_email} via Mailjet")
        else:
            logging.error(f"Mailjet error: {result.status_code} - {result.json()}")
    except Exception as e:
        logging.error(f"Failed to send email via Mailjet: {str(e)}")


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> None:
    """Send email using the configured method (Mailjet preferred, fallback to SMTP)"""
    if not can_send_email():
        logging.warning("No email service configured")
        return

    # Prefer Mailjet if configured
    if (hasattr(settings, 'MAILJET_API_KEY') and 
        hasattr(settings, 'MAILJET_SECRET_KEY') and 
        hasattr(settings, 'MAILJET_SENDER') and
        settings.MAILJET_API_KEY and 
        settings.MAILJET_SECRET_KEY and 
        settings.MAILJET_SENDER):
        send_email_mailjet(to_email, subject, body_text, body_html)
    # Fallback to SMTP
    elif settings.SMTP_HOST and settings.SMTP_SENDER:
        send_email_smtp(to_email, subject, body_text, body_html)

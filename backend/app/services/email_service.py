
from __future__ import annotations

import json
import smtplib
import ssl
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


class EmailServiceError(Exception):
    """Raised when an email cannot be accepted by the configured provider."""


class EmailService:

    @staticmethod
    def send_email(
        *,
        recipient: str,
        subject: str,
        message: str,
        html_message: str | None = None,
    ) -> None:
        provider = current_app.config.get(
            "EMAIL_PROVIDER", "smtp"
        ).lower()

        if provider == "google_apps_script":
            EmailService._send_via_google_apps_script(
                recipient=recipient,
                subject=subject,
                message=message,
                html_message=html_message,
            )

        elif provider == "resend":
            EmailService._send_via_resend(
                recipient=recipient,
                subject=subject,
                message=message,
                html_message=html_message,
            )

        elif provider == "smtp":
            EmailService._send_via_smtp(
                recipient=recipient,
                subject=subject,
                message=message,
                html_message=html_message,
            )

        else:
            raise EmailServiceError(
                f"Unsupported email provider: {provider}"
            )

    @staticmethod
    def _send_via_google_apps_script(
        *,
        recipient: str,
        subject: str,
        message: str,
        html_message: str | None = None,
    ) -> None:
        api_url = current_app.config.get(
            "GOOGLE_APPS_SCRIPT_URL"
        )
        secret = current_app.config.get(
            "GOOGLE_APPS_SCRIPT_SECRET"
        )

        if not api_url or not secret:
            raise EmailServiceError(
                "Google Apps Script email gateway is not configured."
            )

        payload = {
            "secret": secret,
            "recipient": recipient,
            "subject": subject,
            "message": message,
            "html_message": html_message or "",
        }

        request = Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        timeout = int(
            current_app.config.get(
                "EMAIL_API_TIMEOUT_SECONDS", 20
            )
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

                if not result.get("success"):
                    raise EmailServiceError(
                        "Google Apps Script rejected the email request."
                    )

        except EmailServiceError:
            raise

        except HTTPError as exc:
            raise EmailServiceError(
                f"Google email gateway returned HTTP {exc.code}."
            ) from exc

        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise EmailServiceError(
                "Could not connect to the Google email gateway."
            ) from exc

    @staticmethod
    def _send_via_resend(
        *,
        recipient: str,
        subject: str,
        message: str,
        html_message: str | None = None,
    ) -> None:
        api_key = current_app.config.get("RESEND_API_KEY")
        api_url = current_app.config.get(
            "RESEND_API_URL",
            "https://api.resend.com/emails",
        )
        sender = current_app.config.get("EMAIL_SENDER")

        if not api_key or not sender:
            raise EmailServiceError(
                "Resend email delivery is not configured."
            )

        payload = {
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "text": message,
        }

        if html_message:
            payload["html"] = html_message

        request = Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        timeout = int(
            current_app.config.get("EMAIL_API_TIMEOUT_SECONDS", 15)
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                if not 200 <= response.status < 300:
                    raise EmailServiceError(
                        "The Resend API did not accept the email."
                    )

        except HTTPError as exc:
            raise EmailServiceError(
                f"Resend rejected the email (HTTP {exc.code})."
            ) from exc

        except (URLError, TimeoutError, OSError) as exc:
            raise EmailServiceError(
                "Could not connect to the Resend email API."
            ) from exc

    @staticmethod
    def _send_via_smtp(
        *,
        recipient: str,
        subject: str,
        message: str,
        html_message: str | None = None,
    ) -> None:
        host = current_app.config.get("EMAIL_SMTP_HOST")
        sender = current_app.config.get("EMAIL_SENDER")

        if not host or not sender:
            raise EmailServiceError(
                "Email delivery is not configured."
            )

        email = EmailMessage()
        email["From"] = sender
        email["To"] = recipient
        email["Subject"] = subject
        email.set_content(message)

        if html_message:
            email.add_alternative(
                html_message,
                subtype="html",
            )

        timeout = int(
            current_app.config.get("EMAIL_SMTP_TIMEOUT_SECONDS", 15)
        )
        port = int(current_app.config.get("EMAIL_SMTP_PORT", 587))
        username = current_app.config.get("EMAIL_SMTP_USERNAME")
        password = current_app.config.get("EMAIL_SMTP_PASSWORD")
        use_tls = bool(
            current_app.config.get("EMAIL_SMTP_USE_TLS", True)
        )

        try:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                if use_tls:
                    smtp.starttls(
                        context=ssl.create_default_context()
                    )

                if username:
                    if not password:
                        raise EmailServiceError(
                            "SMTP credentials are incomplete."
                        )
                    smtp.login(username, password)

                refused = smtp.send_message(email)

        except EmailServiceError:
            raise

        except (OSError, smtplib.SMTPException) as exc:
            raise EmailServiceError(
                "The SMTP server could not accept the activation email."
            ) from exc

        if refused:
            raise EmailServiceError(
                "The SMTP server did not accept the activation recipient."
            )

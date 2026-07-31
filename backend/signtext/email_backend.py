"""Email backends that send via HTTP APIs instead of SMTP.

Render's outbound network does not allow SMTP ports (25/465/587), so
django.core.mail's SMTP backend fails with "Network is unreachable" no
matter what credentials are used. Resend and Brevo's APIs are plain HTTPS
(port 443), which Render does allow, so we call them directly with
urllib instead of adding a new SDK dependency.
"""
import json
import re
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

RESEND_API_URL = "https://api.resend.com/emails"
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Some HTTP email APIs sit behind Cloudflare, which blocks Python's default
# "Python-urllib/x.y" User-Agent as a bot signature (Cloudflare error 1010).
_USER_AGENT = "kumpas-backend/1.0 (+https://kumpass.onrender.com)"


def _extract_email(address: str) -> str:
    match = re.search(r"<([^>]+)>", address)
    return match.group(1) if match else address


def _split_display_name(address: str) -> tuple:
    match = re.match(r"^\s*(.*?)\s*<([^>]+)>\s*$", address)
    if match:
        name = match.group(1).strip().strip('"')
        return name, match.group(2)
    return "", address


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not configured")
            return 0

        sent_count = 0
        for message in email_messages:
            payload = {
                "from": message.from_email,
                "to": [_extract_email(addr) for addr in message.to],
                "subject": message.subject,
                "text": message.body,
            }
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                RESEND_API_URL,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": _USER_AGENT,
                },
            )
            try:
                timeout = getattr(settings, "EMAIL_TIMEOUT", 10) or 10
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    if 200 <= response.status < 300:
                        sent_count += 1
                    elif not self.fail_silently:
                        raise RuntimeError(
                            f"Resend API returned status {response.status}"
                        )
            except urllib.error.HTTPError as exc:
                if not self.fail_silently:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                if not self.fail_silently:
                    raise RuntimeError(f"Resend API unreachable: {exc.reason}") from exc

        return sent_count


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        api_key = getattr(settings, "BREVO_API_KEY", "")
        if not api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY is not configured")
            return 0

        sent_count = 0
        for message in email_messages:
            sender_name, sender_email = _split_display_name(message.from_email)
            sender = {"email": sender_email}
            if sender_name:
                sender["name"] = sender_name

            to = []
            for addr in message.to:
                name, email = _split_display_name(addr)
                entry = {"email": email}
                if name:
                    entry["name"] = name
                to.append(entry)

            payload = {
                "sender": sender,
                "to": to,
                "subject": message.subject,
                "textContent": message.body,
            }
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                BREVO_API_URL,
                data=body,
                method="POST",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": _USER_AGENT,
                },
            )
            try:
                timeout = getattr(settings, "EMAIL_TIMEOUT", 10) or 10
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    if 200 <= response.status < 300:
                        sent_count += 1
                    elif not self.fail_silently:
                        raise RuntimeError(
                            f"Brevo API returned status {response.status}"
                        )
            except urllib.error.HTTPError as exc:
                if not self.fail_silently:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"Brevo API error {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                if not self.fail_silently:
                    raise RuntimeError(f"Brevo API unreachable: {exc.reason}") from exc

        return sent_count

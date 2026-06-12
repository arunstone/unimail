"""Outbound mail via SMTP (password accounts) or SMTP XOAUTH2 (Gmail/Outlook)."""

import base64
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from ..models import EmailAccount
from ..security import decrypt_secret
from .sync_service import _ensure_access_token


def send_email(db: Session, account: EmailAccount, to: list[str], cc: list[str],
               bcc: list[str], subject: str, body: str,
               in_reply_to: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = account.email_address
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)

    host = account.smtp_host
    port = account.smtp_port or 587
    if not host:
        raise RuntimeError("No SMTP host configured for this account")

    token = _ensure_access_token(db, account)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if token:
            auth = f"user={account.email_address}\x01auth=Bearer {token}\x01\x01"
            smtp.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth.encode()).decode())
        else:
            smtp.login(account.imap_username or account.email_address,
                       decrypt_secret(account.imap_password_enc))
        smtp.send_message(msg, to_addrs=to + cc + bcc)
    return msg

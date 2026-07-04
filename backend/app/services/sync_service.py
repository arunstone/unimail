"""Per-account sync orchestration + the APScheduler background job."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import Attachment, Contact, Email, EmailAccount, Folder, SyncLog
from ..security import decrypt_secret, encrypt_secret
from . import imap_service, oauth

logger = logging.getLogger("unimail.sync")


def _ensure_access_token(db: Session, account: EmailAccount) -> str | None:
    """Returns a valid OAuth access token, refreshing if needed. None for password accounts."""
    if account.provider not in oauth.PROVIDERS:
        return None
    now = datetime.now(timezone.utc)
    expires = account.token_expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires and expires > now + timedelta(minutes=2):
        return decrypt_secret(account.access_token_enc)
    if not account.refresh_token_enc:
        raise RuntimeError("OAuth token expired and no refresh token stored")
    tokens = oauth.refresh_access_token(
        account.provider, decrypt_secret(account.refresh_token_enc)
    )
    account.access_token_enc = encrypt_secret(tokens["access_token"])
    if tokens.get("refresh_token"):
        account.refresh_token_enc = encrypt_secret(tokens["refresh_token"])
    account.token_expires_at = now + timedelta(seconds=tokens.get("expires_in", 3600))
    db.commit()
    return tokens["access_token"]


def connect_account(db: Session, account: EmailAccount):
    token = _ensure_access_token(db, account)
    if token:
        return imap_service.connect(
            account.imap_host, account.imap_port or 993,
            account.email_address, None, oauth_token=token,
        )
    return imap_service.connect(
        account.imap_host, account.imap_port or 993,
        account.imap_username or account.email_address,
        decrypt_secret(account.imap_password_enc),
    )


def _upsert_contact(db: Session, user_id: str, account_id: str,
                    name: str, address: str, seen_at: datetime) -> None:
    address = address.lower().strip()
    if not address or "@" not in address:
        return
    contact = (
        db.query(Contact)
        .filter(Contact.user_id == user_id, Contact.email == address)
        .first()
    )
    if contact is None:
        contact = Contact(user_id=user_id, email=address, name=name or "",
                          account_ids=json.dumps([account_id]))
        db.add(contact)
    else:
        ids = set(json.loads(contact.account_ids or "[]"))
        ids.add(account_id)
        contact.account_ids = json.dumps(sorted(ids))
        if name and not contact.name:
            contact.name = name
    contact.email_count = (contact.email_count or 0) + 1
    if seen_at:
        last = contact.last_seen_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is None or seen_at > last:
            contact.last_seen_at = seen_at


def sync_account(db: Session, account_id: str) -> None:
    account = db.get(EmailAccount, account_id)
    if not account or not account.is_active:
        return

    log = SyncLog(account_id=account.id)
    db.add(log)
    account.sync_status = "syncing"
    db.commit()

    new_count = 0
    try:
        client = connect_account(db, account)
        try:
            for folder_name, role in imap_service.list_folders(client):
                folder = (
                    db.query(Folder)
                    .filter(Folder.account_id == account.id, Folder.name == folder_name)
                    .first()
                )
                if folder is None:
                    folder = Folder(account_id=account.id, name=folder_name, role=role)
                    db.add(folder)
                    db.commit()

                messages, max_uid, uidvalidity = imap_service.fetch_new_messages(
                    client, folder_name, folder.last_seen_uid
                )
                if uidvalidity and folder.uidvalidity and uidvalidity != folder.uidvalidity:
                    # mailbox was rebuilt server-side; UIDs are no longer
                    # comparable — detach them so the refetch below reclaims
                    # rows by Message-ID instead of colliding on stale UIDs
                    db.query(Email).filter(
                        Email.account_id == account.id,
                        Email.folder_name == folder_name,
                    ).update({Email.imap_uid: None}, synchronize_session=False)
                    folder.last_seen_uid = 0
                    db.commit()
                    messages, max_uid, uidvalidity = imap_service.fetch_new_messages(
                        client, folder_name, 0
                    )
                folder.uidvalidity = uidvalidity

                for parsed in messages:
                    exists = (
                        db.query(Email.id)
                        .filter(
                            Email.account_id == account.id,
                            Email.folder_name == folder_name,
                            Email.imap_uid == parsed.imap_uid,
                        )
                        .first()
                    )
                    if exists:
                        continue
                    # reclaim rows whose server location we lost or never had:
                    # locally-stored sent mail, moved messages, UIDVALIDITY
                    # resets — all keyed by Message-ID with a detached UID
                    if parsed.message_id:
                        reclaim = (
                            db.query(Email)
                            .filter(
                                Email.account_id == account.id,
                                Email.message_id == parsed.message_id,
                                Email.imap_uid.is_(None),
                            )
                            .first()
                        )
                        if reclaim is not None:
                            reclaim.folder_name = folder_name
                            reclaim.folder_role = role
                            reclaim.imap_uid = parsed.imap_uid
                            reclaim.is_read = parsed.is_read
                            reclaim.is_starred = parsed.is_starred
                            if not reclaim.body_html and parsed.body_html:
                                reclaim.body_html = parsed.body_html
                            continue
                    row = Email(
                        account_id=account.id,
                        folder_role=role,
                        folder_name=folder_name,
                        imap_uid=parsed.imap_uid,
                        message_id=parsed.message_id,
                        from_name=parsed.from_name,
                        from_email=parsed.from_email,
                        to_recipients=json.dumps(parsed.to),
                        cc_recipients=json.dumps(parsed.cc),
                        bcc_recipients=json.dumps(parsed.bcc),
                        subject=parsed.subject,
                        preview=parsed.preview,
                        body_text=parsed.body_text,
                        body_html=parsed.body_html,
                        is_read=parsed.is_read,
                        is_starred=parsed.is_starred,
                        has_attachments=bool(parsed.attachments),
                        received_at=parsed.received_at,
                    )
                    db.add(row)
                    db.flush()
                    for att in parsed.attachments:
                        db.add(Attachment(email_id=row.id, **att))
                    # contacts from To/From/Cc
                    _upsert_contact(db, account.user_id, account.id,
                                    parsed.from_name, parsed.from_email, parsed.received_at)
                    for addr in parsed.to + parsed.cc:
                        _upsert_contact(db, account.user_id, account.id,
                                        addr["name"], addr["email"], parsed.received_at)
                    new_count += 1

                folder.last_seen_uid = max_uid
                db.commit()

                # refresh read/star flags for messages we already have
                if folder.last_seen_uid:
                    flag_map = imap_service.fetch_flag_updates(client, folder_name)
                    if flag_map:
                        existing = (
                            db.query(Email)
                            .filter(
                                Email.account_id == account.id,
                                Email.folder_name == folder_name,
                                Email.imap_uid.in_(list(flag_map.keys())),
                            )
                            .all()
                        )
                        for row in existing:
                            is_read, is_starred = flag_map[row.imap_uid]
                            row.is_read = is_read
                            row.is_starred = is_starred
                        db.commit()
        finally:
            try:
                client.logout()
            except Exception:
                pass

        account.sync_status = "ok"
        account.sync_error = None
        account.last_synced_at = datetime.now(timezone.utc)
        log.status = "ok"
        log.new_emails = new_count
    except Exception as exc:
        logger.exception("Sync failed for account %s", account.email_address)
        db.rollback()
        account.sync_status = "error"
        account.sync_error = str(exc)[:1000]
        log.status = "error"
        log.detail = str(exc)[:1000]
    finally:
        log.finished_at = datetime.now(timezone.utc)
        db.commit()


def sync_all_accounts() -> None:
    """Scheduler entry point: sync every active account sequentially."""
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        ids = [a.id for a in db.query(EmailAccount).filter(EmailAccount.is_active.is_(True))]
    finally:
        db.close()

    for account_id in ids:
        db = SessionLocal()
        try:
            sync_account(db, account_id)
        finally:
            db.close()

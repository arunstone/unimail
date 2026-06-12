import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Email, EmailAccount, User
from ..schemas import AccountOut, ImapAccountIn
from ..security import encrypt_secret
from ..services import oauth
from ..services.sync_service import sync_account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _unread_counts(db: Session, user_id: str) -> dict[str, int]:
    rows = (
        db.query(Email.account_id, func.count(Email.id))
        .join(EmailAccount, EmailAccount.id == Email.account_id)
        .filter(
            EmailAccount.user_id == user_id,
            Email.is_read.is_(False),
            Email.folder_role == "inbox",
        )
        .group_by(Email.account_id)
        .all()
    )
    return dict(rows)


@router.get("", response_model=list[AccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).all()
    unread = _unread_counts(db, user.id)
    out = []
    for a in accounts:
        item = AccountOut.model_validate(a)
        item.unread_count = unread.get(a.id, 0)
        out.append(item)
    return out


@router.delete("/{account_id}", status_code=204)
def disconnect_account(
    account_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    account = db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()


def _first_sync(account_id: str) -> None:
    db = SessionLocal()
    try:
        sync_account(db, account_id)
    finally:
        db.close()


@router.post("/imap", response_model=AccountOut, status_code=201)
def connect_imap(
    data: ImapAccountIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(EmailAccount)
        .filter(
            EmailAccount.user_id == user.id,
            EmailAccount.email_address == data.email_address.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(409, "This account is already connected")

    provider = "yahoo" if "yahoo" in data.imap_host.lower() else "imap"
    account = EmailAccount(
        user_id=user.id,
        provider=provider,
        email_address=data.email_address.lower(),
        display_name=data.display_name,
        imap_host=data.imap_host,
        imap_port=data.imap_port,
        imap_username=data.imap_username,
        imap_password_enc=encrypt_secret(data.imap_password),
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    background.add_task(_first_sync, account.id)
    return AccountOut.model_validate(account)


@router.get("/oauth/{provider}/start")
def oauth_start(provider: str, token: str, db: Session = Depends(get_db)):
    """Browser is redirected here by the frontend with ?token=<JWT>.
    We validate the JWT, then redirect to the provider's consent page."""
    from ..security import decode_access_token

    if provider not in oauth.PROVIDERS:
        raise HTTPException(
            400,
            "Unsupported OAuth provider. Yahoo and generic IMAP accounts connect "
            "with an app password via POST /api/accounts/imap.",
        )
    cfg = oauth.PROVIDERS[provider]
    if not cfg["client_id"]():
        raise HTTPException(
            501, f"OAuth for {provider} is not configured (missing client id/secret in .env)"
        )
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    return RedirectResponse(oauth.build_consent_url(provider, user_id))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    background: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    fail = f"{settings.frontend_origin}/?oauth_error="
    if error or not code or not state:
        return RedirectResponse(f"{fail}{error or 'missing_code'}")
    payload = oauth.read_state(state)
    if not payload or payload.get("provider") != provider:
        return RedirectResponse(f"{fail}bad_state")

    try:
        tokens = await asyncio.to_thread(oauth.exchange_code, provider, code)
        email_address = (
            await asyncio.to_thread(oauth.fetch_account_email, provider, tokens)
        ).lower()
    except Exception:
        return RedirectResponse(f"{fail}token_exchange_failed")

    cfg = oauth.PROVIDERS[provider]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))

    account = (
        db.query(EmailAccount)
        .filter(
            EmailAccount.user_id == payload["sub"],
            EmailAccount.email_address == email_address,
        )
        .first()
    )
    if account is None:
        account = EmailAccount(
            user_id=payload["sub"],
            provider=provider,
            email_address=email_address,
            imap_host=cfg["imap_host"],
            imap_port=993,
            smtp_host=cfg["smtp_host"],
            smtp_port=587,
        )
        db.add(account)

    account.access_token_enc = encrypt_secret(tokens["access_token"])
    if tokens.get("refresh_token"):
        account.refresh_token_enc = encrypt_secret(tokens["refresh_token"])
    account.token_expires_at = expires_at
    account.is_active = True
    db.commit()
    db.refresh(account)

    background.add_task(_first_sync, account.id)
    return RedirectResponse(f"{settings.frontend_origin}/?connected={account.email_address}")

"""OAuth2 flows for Gmail and Outlook. Both providers end up as IMAP
accounts authenticated with XOAUTH2, so the sync code path is identical
to plain-password IMAP accounts."""

from datetime import datetime, timedelta, timezone

import jwt
import requests

from ..config import settings

PROVIDERS = {
    "gmail": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "https://mail.google.com/ https://www.googleapis.com/auth/userinfo.email",
        "imap_host": "imap.gmail.com",
        "smtp_host": "smtp.gmail.com",
        "client_id": lambda: settings.google_client_id,
        "client_secret": lambda: settings.google_client_secret,
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
    },
    "outlook": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": None,  # email comes from the id_token
        "scopes": (
            "offline_access openid email "
            "https://outlook.office.com/IMAP.AccessAsUser.All "
            "https://outlook.office.com/SMTP.Send"
        ),
        "imap_host": "outlook.office365.com",
        "smtp_host": "smtp.office365.com",
        "client_id": lambda: settings.outlook_client_id,
        "client_secret": lambda: settings.outlook_client_secret,
        "extra_auth_params": {},
    },
}


def redirect_uri(provider: str) -> str:
    return f"{settings.backend_url}/api/accounts/oauth/{provider}/callback"


def make_state(user_id: str, provider: str) -> str:
    payload = {
        "sub": user_id,
        "provider": provider,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        "purpose": "oauth_state",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_state(state: str) -> dict | None:
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "oauth_state":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def build_consent_url(provider: str, user_id: str) -> str:
    cfg = PROVIDERS[provider]
    params = {
        "client_id": cfg["client_id"](),
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scopes"],
        "state": make_state(user_id, provider),
        **cfg["extra_auth_params"],
    }
    return f"{cfg['auth_url']}?{requests.compat.urlencode(params)}"


def exchange_code(provider: str, code: str) -> dict:
    """Returns the raw token response: access_token, refresh_token, expires_in, id_token?"""
    cfg = PROVIDERS[provider]
    resp = requests.post(
        cfg["token_url"],
        data={
            "client_id": cfg["client_id"](),
            "client_secret": cfg["client_secret"](),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri(provider),
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(provider: str, refresh_token: str) -> dict:
    cfg = PROVIDERS[provider]
    data = {
        "client_id": cfg["client_id"](),
        "client_secret": cfg["client_secret"](),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    if provider == "outlook":
        data["scope"] = cfg["scopes"]
    resp = requests.post(cfg["token_url"], data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_account_email(provider: str, token_response: dict) -> str:
    """Determine the mailbox address for the freshly connected account."""
    cfg = PROVIDERS[provider]
    if cfg["userinfo_url"]:
        resp = requests.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {token_response['access_token']}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["email"]
    # Outlook: decode the id_token (signature already implied by TLS exchange)
    id_token = token_response.get("id_token", "")
    claims = jwt.decode(id_token, options={"verify_signature": False})
    return claims.get("email") or claims.get("preferred_username", "")

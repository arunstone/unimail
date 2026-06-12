import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Contact, Email, EmailAccount, User
from ..schemas import ContactOut, EmailRowOut

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


def _to_out(c: Contact) -> ContactOut:
    return ContactOut(
        id=c.id, name=c.name, email=c.email,
        account_ids=json.loads(c.account_ids or "[]"),
        email_count=c.email_count,
    )


@router.get("", response_model=list[ContactOut])
def list_contacts(
    search: str = "",
    account_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Contact).filter(Contact.user_id == user.id)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Contact.name.ilike(like), Contact.email.ilike(like)))
    if account_id:
        q = q.filter(Contact.account_ids.contains(account_id))
    return [
        _to_out(c)
        for c in q.order_by(Contact.name.asc(), Contact.email.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    ]


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if not contact or contact.user_id != user.id:
        raise HTTPException(404, "Contact not found")
    return _to_out(contact)


@router.get("/{contact_id}/emails", response_model=list[EmailRowOut])
def contact_emails(
    contact_id: str,
    folder: str = "all",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = db.get(Contact, contact_id)
    if not contact or contact.user_id != user.id:
        raise HTTPException(404, "Contact not found")

    address = contact.email
    q = (
        db.query(Email)
        .join(EmailAccount)
        .filter(EmailAccount.user_id == user.id)
        .filter(
            or_(
                Email.from_email == address,
                Email.to_recipients.contains(address),
                Email.cc_recipients.contains(address),
            )
        )
    )
    if folder != "all":
        if folder not in ("inbox", "sent", "drafts"):
            raise HTTPException(400, "folder must be all|inbox|sent|drafts")
        q = q.filter(Email.folder_role == folder)
    else:
        q = q.filter(Email.folder_role.notin_(["trash", "spam"]))
    return (
        q.order_by(Email.received_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

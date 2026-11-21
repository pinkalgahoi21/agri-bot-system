import hashlib
import hmac
import os
import re
import secrets
import time

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import LoginAccount, LoginSession, WebAccount

router = APIRouter(prefix="/auth")


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=256)


class Confirmation(BaseModel):
    email: str = Field(max_length=254)
    token: str = Field(pattern=r"^[0-9]{6}$")
    ticket: str = Field(min_length=32, max_length=128)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=1, maxmem=67108864).hex()


def session(db, account_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.query(LoginSession).filter(LoginSession.expires <= now).delete()
    db.add(LoginSession(digest=digest(token), account_id=account_id, expires=now + 86400))
    db.commit()
    return {"access_token": token}


@router.post("/signup")
def signup(data: Credentials, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Invalid email")
    key, sender = os.getenv("RESEND_API_KEY"), os.getenv("AUTH_EMAIL_FROM")
    if not key or not sender:
        raise HTTPException(503, "Signup email delivery is not configured")
    row = db.query(LoginAccount).filter_by(email=email).with_for_update().first()
    now = int(time.time())
    ticket = secrets.token_urlsafe(32)
    if row and row.account_id:
        return {"ticket": ticket}
    if row and now - row.issued < 60:
        raise HTTPException(429, "Wait before requesting another code")
    if not row:
        row = LoginAccount(email=email)
        db.add(row)
    salt = secrets.token_hex(16)
    code = f"{secrets.randbelow(1000000):06}"
    row.password_hash = salt + ":" + password_hash(data.password, salt)
    row.challenge, row.issued, row.attempts = digest(ticket + code), now, 0
    try:
        db.flush()
        requests.post("https://api.resend.com/emails", headers={"Authorization": "Bearer " + key},
                      json={"from": sender, "to": [email], "subject": "Verify your Agri-Bot account",
                            "text": f"Your signup code is {code}. It expires in 5 minutes."}, timeout=10).raise_for_status()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(429, "Retry later")
    except requests.RequestException:
        db.rollback()
        raise HTTPException(503, "Email delivery unavailable")
    return {"ticket": ticket}


@router.post("/verify")
def verify(data: Confirmation, db: Session = Depends(get_db)):
    row = db.query(LoginAccount).filter_by(email=data.email.strip().lower()).with_for_update().first()
    if not row or not row.challenge or row.attempts >= 5 or time.time() - row.issued >= 300:
        raise HTTPException(400, "Invalid or expired challenge")
    if not hmac.compare_digest(row.challenge, digest(data.ticket + data.token)):
        row.attempts += 1
        db.commit()
        raise HTTPException(400, "Incorrect code")
    account = WebAccount(subject="local:" + secrets.token_hex(16))
    db.add(account)
    db.flush()
    row.account_id, row.challenge = account.id, None
    return session(db, account.id)


@router.post("/login")
def login(data: Credentials, db: Session = Depends(get_db)):
    row = db.query(LoginAccount).filter_by(email=data.email.strip().lower()).with_for_update().first()
    now = int(time.time())
    if row and row.account_id and row.attempts >= 8 and now - row.issued < 300:
        raise HTTPException(429, "Retry later")
    salt, expected = row.password_hash.split(":") if row else ("00" * 16, "00" * 64)
    if not hmac.compare_digest(password_hash(data.password, salt), expected) or not row or not row.account_id:
        if row and row.account_id:
            if now - row.issued >= 300:
                row.attempts = 0
            row.issued, row.attempts = now, row.attempts + 1
            db.commit()
        raise HTTPException(401, "Invalid login")
    row.attempts = 0
    return session(db, row.account_id)

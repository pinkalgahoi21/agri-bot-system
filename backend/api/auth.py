import hashlib
import hmac
import os
import time
from api.local_login import router as login_router, digest
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import LoginSession, Farmer

router = APIRouter()

router.include_router(login_router)


@router.post('/auth/logout', status_code=204)
def logout(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    db.query(LoginSession).filter_by(digest=digest(credentials.credentials)).delete()
    db.commit()

def bot_signature(user_id, timestamp):
    message = f'agribot-internal:{user_id}:{timestamp}'.encode()
    return hmac.new(os.environ['TELEGRAM_TOKEN'].encode(), message, hashlib.sha256).hexdigest()

def identity(request: Request, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)), db: Session = Depends(get_db)):
    internal = request.headers.get('X-Bot-Signature')
    if internal is not None:
        try:
            user_id = int(request.headers.get('X-Bot-User', ''))
            timestamp = int(request.headers.get('X-Bot-Time', ''))
            if os.getenv('TELEGRAM_TOKEN') and 0 < user_id < 2**63 and abs(time.time() - timestamp) < 60 and hmac.compare_digest(internal.encode(), bot_signature(user_id, timestamp).encode()):
                return user_id
        except ValueError:
            pass
        raise HTTPException(401, 'Invalid bot credentials.')
    if not credentials:
        raise HTTPException(401, 'Sign in first.')
    record = db.get(LoginSession, digest(credentials.credentials))
    if not record or record.expires <= time.time():
        raise HTTPException(401, 'Sign in again.')
    return -record.account_id

@router.get('/profile')
def profile(user_id: int = Depends(identity), db: Session = Depends(get_db)):
    farmer = db.get(Farmer, user_id)
    return {'profile': {key: getattr(farmer, key) for key in ('name', 'city', 'crop')} if farmer else None}

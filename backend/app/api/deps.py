import hashlib
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.jwt_utils import decode as jwt_decode, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db import models as db_models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# Für Endpoints, die offen sind, aber mit Login mehr verraten (z. B. ob ein
# Setting bearbeitbar ist)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def passwort_fingerabdruck(user: db_models.User) -> str:
    """Kurzer Fingerabdruck des Passwort-Hashes für den Token (Claim "pwh").
    Neues Passwort → neues Salt → alle vorher ausgestellten Tokens ungültig."""
    return hashlib.sha256(user.hashed_password.encode()).hexdigest()[:16]


def _user_aus_token(token: str, db: Session) -> db_models.User | None:
    try:
        payload = jwt_decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if user is None or not user.aktiv:
        return None
    if not hmac.compare_digest(str(payload.get("pwh", "")), passwort_fingerabdruck(user)):
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> db_models.User:
    user = _user_aus_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldedaten",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> db_models.User | None:
    return _user_aus_token(token, db) if token else None


def ist_admin(user: db_models.User | None) -> bool:
    if user is None:
        return False
    admins = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
    return user.email.lower() in admins

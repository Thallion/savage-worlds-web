import hashlib
import hmac
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from app.jwt_utils import encode as jwt_encode
from sqlalchemy.orm import Session

from app.config import settings
from app.api.deps import get_current_user, passwort_fingerabdruck
from app.db.database import get_db
from app.db import models as db_models
from app.services import charakterbild
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    PasswortAendern,
    AccountLoeschen,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Format: pbkdf2_sha256$<iterationen>$<salt-hex>$<key-hex>. Alte Hashes
# ("<salt-hex>:<key-hex>", 100k Iterationen) werden beim Login umgeschlüsselt.
_PBKDF2_ITERATIONEN = 600_000
_ALT_ITERATIONEN = 100_000


def _pbkdf2(password: str, salt: bytes, iterationen: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterationen)


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = _pbkdf2(password, salt, _PBKDF2_ITERATIONEN)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONEN}${salt.hex()}${key.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        _, iterationen, salt_hex, key_hex = stored.split("$", 3)
        iter_zahl = int(iterationen)
    else:
        salt_hex, key_hex = stored.split(":", 1)
        iter_zahl = _ALT_ITERATIONEN
    key = _pbkdf2(password, bytes.fromhex(salt_hex), iter_zahl)
    return hmac.compare_digest(key.hex(), key_hex)


def _braucht_rehash(stored: str) -> bool:
    return not stored.startswith(f"pbkdf2_sha256${_PBKDF2_ITERATIONEN}$")


def _pruefe_passwort_regeln(password: str) -> None:
    if len(password) < settings.passwort_min_laenge:
        raise HTTPException(
            status_code=400,
            detail=f"Das Passwort muss mindestens {settings.passwort_min_laenge} Zeichen lang sein",
        )


def _create_access_token(user: db_models.User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt_encode(
        {"sub": user.id, "pwh": passwort_fingerabdruck(user), "exp": expire.timestamp()},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(db_models.User).filter(db_models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    if db.query(db_models.User).filter(db_models.User.benutzername == user_in.benutzername).first():
        raise HTTPException(status_code=400, detail="Benutzername bereits vergeben")
    _pruefe_passwort_regeln(user_in.passwort)

    user = db_models.User(
        email=user_in.email,
        benutzername=user_in.benutzername,
        hashed_password=_hash_password(user_in.passwort),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(db_models.User).filter(db_models.User.email == user_in.email).first()
    if not user or not _verify_password(user_in.passwort, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-Mail oder Passwort falsch",
        )
    if _braucht_rehash(user.hashed_password):
        user.hashed_password = _hash_password(user_in.passwort)
        db.commit()
    return Token(access_token=_create_access_token(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: db_models.User = Depends(get_current_user)):
    return current_user


@router.put("/passwort", response_model=Token)
def passwort_aendern(
    data: PasswortAendern,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _verify_password(data.aktuelles_passwort, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Aktuelles Passwort falsch")
    _pruefe_passwort_regeln(data.neues_passwort)
    current_user.hashed_password = _hash_password(data.neues_passwort)
    db.commit()
    # Alte Tokens (auch anderer Geräte) sind ab jetzt ungültig — der
    # aufrufende Client bekommt einen neuen
    return Token(access_token=_create_access_token(current_user))


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def account_loeschen(
    data: AccountLoeschen,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _verify_password(data.passwort, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Passwort falsch")
    bild_ids = [c.bild_id for c in current_user.charaktere if c.bild_id]
    db.delete(current_user)
    db.commit()
    for bild_id in bild_ids:
        charakterbild.loesche(bild_id)

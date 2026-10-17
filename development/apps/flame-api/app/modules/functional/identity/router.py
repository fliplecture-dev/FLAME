"""Supabase Auth exchange and independently verified browser identity."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe, compare_digest
from typing import Annotated
from uuid import UUID

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.modules.functional.identity.import_profiles import lock_profile_email
from app.modules.functional.identity.models import AdminRole, BrowserSession, StudentProfile

from app.modules.functional.identity.profile_data import PhoneInput, clean_phone

router = APIRouter(prefix="/api/v1")
AUTH_FAILED = HTTPException(401, "Authentication required")


class RegisterBody(PhoneInput):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)

    @field_validator("display_name")
    @classmethod
    def nonblank(cls, value: str):
        if not value.strip():
            raise ValueError("Display name is required")
        return value.strip()


class LoginBody(PhoneInput):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class VerifyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token_hash: str
    type: str


class RecoverBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str


class ResetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session: str
    password: str = Field(min_length=12, max_length=128)


def _config(request: Request) -> Settings:
    return request.app.state.settings


def require_bff(request: Request, x_bff_key: Annotated[str | None, Header()] = None):
    key = _config(request).bff_shared_key
    if key is None or x_bff_key is None or not compare_digest(x_bff_key, key.get_secret_value()):
        raise HTTPException(403, "Forbidden")


def _provider(settings: Settings, method: str, path: str, *, body: dict | None = None, token: str | None = None):
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(503, "Identity service unavailable")
    headers = {"apikey": settings.supabase_anon_key.get_secret_value()}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        response = httpx.request(method, settings.supabase_url + "/auth/v1" + path,
                                 json=body, headers=headers, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(503, "Identity service unavailable")
    if response.status_code >= 500:
        raise HTTPException(503, "Identity service unavailable")
    if response.status_code == 429:
        raise HTTPException(429, "Please wait before trying again")
    if response.status_code >= 400:
        raise AUTH_FAILED
    return response.json() if response.content else {}


def verify_access_token(settings: Settings, token: str) -> dict:
    """Never accept client claims without Supabase signature and claim checks."""
    if not settings.supabase_url:
        raise AUTH_FAILED
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm == "HS256" and settings.supabase_jwt_secret:
            key = settings.supabase_jwt_secret.get_secret_value()
        elif algorithm in ("RS256", "ES256"):
            key = jwt.PyJWKClient(settings.supabase_url + "/auth/v1/.well-known/jwks.json").get_signing_key_from_jwt(token).key
        else:
            raise AUTH_FAILED
        claims = jwt.decode(token, key, algorithms=[algorithm],
                            issuer=settings.supabase_url + "/auth/v1",
                            audience=settings.supabase_jwt_audience,
                            options={"require": ["iss", "aud", "exp", "sub", "iat"]},
                            leeway=15)
        if not isinstance(claims["sub"], str) or claims.get("role") != "authenticated":
            raise AUTH_FAILED
        UUID(claims["sub"])
        return claims
    except (jwt.PyJWTError, ValueError, KeyError, httpx.HTTPError):
        raise AUTH_FAILED


def _cipher(settings: Settings) -> Fernet:
    if not settings.session_encryption_key:
        raise HTTPException(503, "Session storage unavailable")
    try:
        return Fernet(settings.session_encryption_key.get_secret_value().encode())
    except ValueError:
        raise HTTPException(503, "Session storage unavailable")


def _store(request: Request, payload: dict) -> str:
    settings = _config(request)
    claims = verify_access_token(settings, payload["access_token"])
    expires = datetime.fromtimestamp(claims["exp"], timezone.utc)
    raw = token_urlsafe(48)
    cipher = _cipher(settings)
    db = request.app.state.database
    with db.session() as session, session.begin():
        session.add(BrowserSession(
            id_hash=sha256(raw.encode()).hexdigest(), auth_subject=claims["sub"],
            access_token=cipher.encrypt(payload["access_token"].encode()),
            refresh_token=cipher.encrypt(payload["refresh_token"].encode()),
            expires_at=expires))
    return raw


def _session(request: Request, raw: str | None, *, refresh: bool = True):
    if not raw or len(raw) > 200:
        raise AUTH_FAILED
    db = request.app.state.database
    settings = _config(request)
    failed_refresh = False
    with db.session() as session, session.begin():
        row = session.scalar(select(BrowserSession).where(
            BrowserSession.id_hash == sha256(raw.encode()).hexdigest()).with_for_update())
        if row is None or row.revoked_at is not None:
            raise AUTH_FAILED
        if row.created_at <= datetime.now(timezone.utc) - timedelta(days=7):
            raise AUTH_FAILED
        cipher = _cipher(settings)
        try:
            access = cipher.decrypt(row.access_token).decode()
            refresh_token = cipher.decrypt(row.refresh_token).decode()
        except InvalidToken:
            raise AUTH_FAILED
        if row.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30):
            if not refresh:
                raise AUTH_FAILED
            try:
                tokens = _provider(settings, "POST", "/token?grant_type=refresh_token",
                                   body={"refresh_token": refresh_token})
                claims = verify_access_token(settings, tokens["access_token"])
                if claims["sub"] != row.auth_subject:
                    raise AUTH_FAILED
                row.access_token = cipher.encrypt(tokens["access_token"].encode())
                row.refresh_token = cipher.encrypt(tokens["refresh_token"].encode())
                row.expires_at = datetime.fromtimestamp(claims["exp"], timezone.utc)
                access = tokens["access_token"]
            except (KeyError, HTTPException):
                row.revoked_at = datetime.now(timezone.utc)
                failed_refresh = True
        if not failed_refresh:
            claims = verify_access_token(settings, access)
            if claims["sub"] != row.auth_subject:
                raise AUTH_FAILED
    if failed_refresh:
        raise AUTH_FAILED
    return claims, access


def _principal(request: Request, raw: str):
    claims, access = _session(request, raw)
    with request.app.state.database.session() as session, session.begin():
        existing = session.scalar(select(StudentProfile).where(StudentProfile.auth_subject == claims["sub"]))
        if existing is None and claims.get("email"):
            lock_profile_email(session, claims["email"])
            pending = session.scalars(select(StudentProfile).where(StudentProfile.status == "pending",
                StudentProfile.auth_subject.like("bulk-pending:%"),
                func.lower(StudentProfile.email) == claims["email"].strip().lower()).with_for_update()).all()
            if pending:
                # Never bind an imported profile using a client-provided email or unverified claims alone.
                user = _provider(_config(request), "GET", "/user", token=access)
                if (len(pending) != 1 or not user.get("email_confirmed_at") or user.get("id") != claims["sub"] or
                        str(user.get("email", "")).strip().lower() != claims["email"].strip().lower()):
                    raise AUTH_FAILED
                pending[0].auth_subject = claims["sub"]
                pending[0].status = "active"
                session.flush()
                existing = pending[0]

        if existing is None:
            try:
                phone = clean_phone((claims.get("user_metadata") or {}).get("phone_number"))
            except ValueError:
                phone = None
            session.execute(insert(StudentProfile).values(
                auth_subject=claims["sub"], email=claims.get("email"), phone_number=phone,
                display_name=(claims.get("user_metadata") or {}).get("display_name")
            ).on_conflict_do_nothing(index_elements=["auth_subject"]))
        profile = existing or session.scalar(select(StudentProfile).where(StudentProfile.auth_subject == claims["sub"]))
        if profile.status != "active":
            raise HTTPException(403, "Account inactive")
        admin = session.get(AdminRole, claims["sub"]) is not None
        return {"id": str(profile.id), "display_name": profile.display_name,
                "email": profile.email, "role": "admin" if admin else "member"}


@router.post("/auth/register", dependencies=[Depends(require_bff)])
def register(request: Request, body: RegisterBody):
    try:
        result = _provider(_config(request), "POST", "/signup", body={
            "email": body.email.strip().lower(), "password": body.password,
            "data": {"display_name": body.display_name.strip(), **({"phone_number": body.phone_number} if body.phone_number else {})},
        })
        if result.get("access_token"):
            raise HTTPException(503, "Email verification must be enabled")
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        # Supabase may reject an already registered address. Keep the response identical.
        pass
    # Identical response for new and existing addresses.
    return {"status": "verification_pending"}


@router.post("/auth/login", dependencies=[Depends(require_bff)])
def login(request: Request, body: LoginBody):
    payload = _provider(_config(request), "POST", "/token?grant_type=password",
                        body={"email": body.email.strip().lower(), "password": body.password})
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise AUTH_FAILED
    user = _provider(_config(request), "GET", "/user", token=payload["access_token"])
    if not user.get("email_confirmed_at"):
        raise AUTH_FAILED
    raw = _store(request, payload)
    if body.phone_number:
        principal = _principal(request, raw)
        with request.app.state.database.session() as db, db.begin():
            profile = db.scalar(select(StudentProfile).where(StudentProfile.id == UUID(principal["id"])).with_for_update())
            if profile is None or profile.status != "active":
                raise HTTPException(403, "Account inactive")
            profile.phone_number = body.phone_number
    return {"session": raw}



@router.post("/auth/verify", dependencies=[Depends(require_bff)])
def verify(request: Request, body: VerifyBody):
    if body.type not in ("signup", "recovery", "email"):
        raise HTTPException(422, "Invalid verification type")
    payload = _provider(_config(request), "POST", "/verify",
                        body={"token_hash": body.token_hash, "type": body.type})
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise AUTH_FAILED
    return {"session": _store(request, payload), "type": body.type}


@router.post("/auth/recover", dependencies=[Depends(require_bff)])
def recover(request: Request, body: RecoverBody):
    try:
        _provider(_config(request), "POST", "/recover", body={
            "email": body.email.strip().lower(),
        })
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    return {"status": "recovery_sent"}


@router.post("/auth/reset-password", dependencies=[Depends(require_bff)])
def reset_password(request: Request, body: ResetBody):
    _, access = _session(request, body.session)
    _provider(_config(request), "PUT", "/user", body={"password": body.password}, token=access)
    return {"status": "password_updated"}


@router.post("/auth/refresh", dependencies=[Depends(require_bff)])
def refresh(request: Request, x_flame_session: Annotated[str | None, Header()] = None):
    _session(request, x_flame_session)
    return {"status": "active"}


@router.post("/auth/logout", dependencies=[Depends(require_bff)])
def logout(request: Request, x_flame_session: Annotated[str | None, Header()] = None):
    if x_flame_session:
        try:
            _, access = _session(request, x_flame_session, refresh=False)
            _provider(_config(request), "POST", "/logout", token=access)
        except HTTPException:
            pass
        with request.app.state.database.session() as session, session.begin():
            row = session.get(BrowserSession, sha256(x_flame_session.encode()).hexdigest())
            if row:
                row.revoked_at = datetime.now(timezone.utc)
    return {"status": "signed_out"}


@router.get("/me", dependencies=[Depends(require_bff)])
def me(request: Request, x_flame_session: Annotated[str | None, Header()] = None):
    return _principal(request, x_flame_session)


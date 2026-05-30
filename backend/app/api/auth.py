from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.db import get_db
from app.models.user import User
from app.models.scenario import Scenario
from app.security import (
    create_access_token,
    create_email_token,
    decode_email_token,
    create_password_reset_token,
    decode_password_reset_token,
    get_current_user_id,
    require_self,
)
from app.services.email import send_verification_email, send_password_reset_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    password: str
    target_zip: str | None = None


class ProfileRequest(BaseModel):
    annual_income: float
    savings: float
    down_payment: float
    credit_score: int
    monthly_debt_car: float = 0
    monthly_debt_student: float = 0
    monthly_debt_credit: float = 0
    monthly_debt_other: float = 0
    zip_code: str
    # Enhanced financial profile (Phase 4)
    liquid_savings: float | None = None
    brokerage_value: float | None = None
    retirement_value: float | None = None
    monthly_take_home: float | None = None


class LoginRequest(BaseModel):
    identifier: str  # email OR username
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    first_name: str
    target_zip: str | None = None
    email_verified: bool = False


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Helpers ───────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


async def _get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check uniqueness
    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_user = await db.execute(select(User).where(User.username == body.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        username=body.username,
        hashed_password=_hash_password(body.password),
        target_zip=body.target_zip,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Best-effort verification email — send_verification_email never raises.
    await send_verification_email(user.email, user.first_name, create_email_token(user.id))

    return TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        target_zip=user.target_zip,
        email_verified=user.email_verified,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Accept either an email address or a username as the identifier.
    ident = body.identifier.strip()
    result = await db.execute(
        select(User).where(or_(User.email == ident, User.username == ident))
    )
    user = result.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        target_zip=user.target_zip,
        email_verified=user.email_verified,
    )


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Confirm a user's email address from a verification-link token."""
    user_id = decode_email_token(body.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.email_verified:
        user.email_verified = True
        await db.commit()
    return {"email_verified": True}


@router.post("/resend-verification/{user_id}")
async def resend_verification(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Re-send the verification email to the authenticated user."""
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        return {"status": "already_verified"}
    sent = await send_verification_email(user.email, user.first_name, create_email_token(user.id))
    return {"status": "sent" if sent else "skipped"}


@router.post("/profile/{user_id}")
async def save_profile_for_user(
    user_id: int,
    body: ProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.annual_income = body.annual_income
    user.savings = body.savings
    user.down_payment = body.down_payment
    user.credit_score = body.credit_score
    user.monthly_debt_car = body.monthly_debt_car
    user.monthly_debt_student = body.monthly_debt_student
    user.monthly_debt_credit = body.monthly_debt_credit
    user.monthly_debt_other = body.monthly_debt_other
    user.zip_code = body.zip_code
    if body.zip_code:
        user.target_zip = body.zip_code  # keep target_zip in sync for map centering
    user.liquid_savings = body.liquid_savings
    user.brokerage_value = body.brokerage_value
    user.retirement_value = body.retirement_value
    user.monthly_take_home = body.monthly_take_home

    await db.commit()
    await db.refresh(user)

    return {
        "user_id": user.id,
        "annual_income": user.annual_income,
        "savings": user.savings,
        "down_payment": user.down_payment,
        "credit_score": user.credit_score,
        "monthly_debt_car": user.monthly_debt_car,
        "monthly_debt_student": user.monthly_debt_student,
        "monthly_debt_credit": user.monthly_debt_credit,
        "monthly_debt_other": user.monthly_debt_other,
        "zip_code": user.zip_code,
        "liquid_savings": user.liquid_savings,
        "brokerage_value": user.brokerage_value,
        "retirement_value": user.retirement_value,
        "monthly_take_home": user.monthly_take_home,
    }


@router.get("/me/{user_id}")
async def get_me(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Resolve the primary scenario pointer to its public_id (only if still active).
    primary_scenario_public_id = None
    if user.primary_scenario_id is not None:
        primary = await db.scalar(
            select(Scenario).where(
                Scenario.id == user.primary_scenario_id,
                Scenario.is_active == True,
            )
        )
        if primary:
            primary_scenario_public_id = primary.public_id

    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
        "email_verified": user.email_verified,
        "annual_income": user.annual_income,
        "savings": user.savings,
        "down_payment": user.down_payment,
        "credit_score": user.credit_score,
        "monthly_debt_car": user.monthly_debt_car or 0,
        "monthly_debt_student": user.monthly_debt_student or 0,
        "monthly_debt_credit": user.monthly_debt_credit or 0,
        "monthly_debt_other": user.monthly_debt_other or 0,
        "zip_code": user.zip_code,
        "target_zip": user.target_zip,
        "liquid_savings": user.liquid_savings,
        "brokerage_value": user.brokerage_value,
        "retirement_value": user.retirement_value,
        "monthly_take_home": user.monthly_take_home,
        "primary_scenario_public_id": primary_scenario_public_id,
    }


@router.patch("/target-zip/{user_id}")
async def update_target_zip(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.target_zip = body.get("target_zip")
    await db.commit()
    return {"target_zip": user.target_zip}


# ── Account self-service (profile page) ───────────────────────

class AccountUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.patch("/account/{user_id}")
async def update_account(
    user_id: int,
    body: AccountUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Update the user's name and/or email address."""
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email and body.email != user.email:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = body.email
    if body.first_name is not None:
        user.first_name = body.first_name.strip()
    if body.last_name is not None:
        user.last_name = body.last_name.strip()

    await db.commit()
    await db.refresh(user)
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
    }


@router.post("/change-password/{user_id}")
async def change_password(
    user_id: int,
    body: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Change the user's password after verifying the current one."""
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    user.hashed_password = _hash_password(body.new_password)
    await db.commit()
    return {"status": "ok"}


# ── Password reset (unauthenticated, email-token flow) ─────────────────────

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Email a reset link if the address belongs to a user.

    Always returns 200 with the same body — never reveals whether the
    address is registered (standard practice to avoid email enumeration).
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        token = create_password_reset_token(user.id)
        await send_password_reset_email(user.email, user.first_name, token)
    return {"status": "ok"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Set a new password using a valid reset token from the email link."""
    user_id = decode_password_reset_token(body.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    user.hashed_password = _hash_password(body.new_password)
    await db.commit()
    return {"status": "ok"}


# ── Delete account (authenticated, irreversible) ───────────────────────────

@router.delete("/account/{user_id}", status_code=204)
async def delete_account(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Hard-delete the user's account and all associated scenarios.

    Other tables that reference users (forecast_realizations, etc.) use
    nullable user_id or cascade rules at the model level. Scenarios are
    deleted explicitly because they're user-owned.
    """
    require_self(user_id, current_user_id)
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Wipe scenarios first (no DB-level cascade for portability).
    await db.execute(
        Scenario.__table__.delete().where(Scenario.user_id == user_id)
    )
    await db.delete(user)
    await db.commit()
    return None

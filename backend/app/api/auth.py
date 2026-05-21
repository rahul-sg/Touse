import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.db import get_db
from app.models.user import User

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

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
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    first_name: str
    target_zip: str | None = None


# ── Helpers ───────────────────────────────────────────────────

def _make_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


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

    return TokenResponse(
        access_token=_make_token(user.id),
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        target_zip=user.target_zip,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=_make_token(user.id),
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        target_zip=user.target_zip,
    )


@router.post("/profile")
async def save_profile(body: ProfileRequest, db: AsyncSession = Depends(get_db)):
    """Save financial profile — called with Authorization header carrying the JWT."""
    from fastapi import Request
    raise HTTPException(status_code=501, detail="Use /profile-authed endpoint")


@router.post("/profile/{user_id}")
async def save_profile_for_user(
    user_id: int,
    body: ProfileRequest,
    db: AsyncSession = Depends(get_db),
):
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
async def get_me(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
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
    }


@router.patch("/target-zip/{user_id}")
async def update_target_zip(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.target_zip = body.get("target_zip")
    await db.commit()
    return {"target_zip": user.target_zip}

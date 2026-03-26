from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import User, Subscription, UserRole, SubscriptionTier
from auth_utils import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    role: str | None = "freelancer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value if user.role else "freelancer",
        "trust_score": user.trust_score or 100,
        "wallet_address": user.wallet_address,
    }


@router.post("/signup")
def signup(req: SignUpRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = UserRole.CLIENT if req.role == "client" else UserRole.FREELANCER

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name or None,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-create free subscription
    sub = Subscription(user_id=user.id, tier=SubscriptionTier.FREE)
    db.add(sub)
    db.commit()

    token = create_token({"sub": str(user.id), "email": user.email})
    return {"ok": True, "token": token, "user": _user_response(user)}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token({"sub": str(user.id), "email": user.email})
    return {"ok": True, "token": token, "user": _user_response(user)}

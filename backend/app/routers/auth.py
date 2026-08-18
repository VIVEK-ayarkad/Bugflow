from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User, UserRole
from app.schemas import Token, UserCreate, UserLogin, UserProfileUpdate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_role_str(role) -> str:
    if hasattr(role, "value"):
        return role.value
    return str(role)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username is taken")

    user_count = db.query(User).count()
    assigned_role = UserRole.ADMIN if user_count == 0 else (payload.role or UserRole.REPORTER)

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=assigned_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, role=_get_role_str(user.role))
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, role=_get_role_str(user.role))
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.username and payload.username.strip() != current_user.username:
        new_username = payload.username.strip()
        existing = db.query(User).filter(User.username == new_username, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username is already taken")
        current_user.username = new_username

    if payload.email and payload.email.strip().lower() != current_user.email.lower():
        new_email = payload.email.strip().lower()
        existing = db.query(User).filter(User.email == new_email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already in use")
        current_user.email = new_email

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password")
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_user.hashed_password = hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user

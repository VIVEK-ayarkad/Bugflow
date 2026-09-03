from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.errors import ErrorResponse
from app.models import User, UserRole
from app.schemas import MessageResponse, Token, UserCreate, UserLogin, UserProfileUpdate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_role_str(role: UserRole | str) -> str:
    if hasattr(role, "value"):
        return role.value
    return str(role)


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Create a new BugFlow user account. If this is the very first user in the system, they are automatically granted the 'admin' role.",
    responses={
        201: {"description": "User successfully registered, JWT access token returned", "model": Token},
        400: {"description": "Email or username already exists", "model": ErrorResponse},
        422: {"description": "Validation error in request payload", "model": ErrorResponse},
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user in BugFlow."""
    clean_email = payload.email.strip().lower()
    clean_username = payload.username.strip()

    if db.query(User).filter(User.email.ilike(clean_email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
    if db.query(User).filter(User.username.ilike(clean_username)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is taken")

    user_count = db.query(User).count()
    assigned_role = UserRole.ADMIN if user_count == 0 else (payload.role or UserRole.REPORTER)

    user = User(
        email=clean_email,
        username=clean_username,
        hashed_password=hash_password(payload.password),
        role=assigned_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        user_id=user.id,
        action="User Registered",
        details=f"New account '{user.username}' created with role '{user.role.value}'",
    )

    token = create_access_token(user_id=user.id, role=_get_role_str(user.role))
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=Token,
    summary="User Login (JSON payload)",
    description="Authenticate with email and password to receive a JWT access token for API authorization.",
    responses={
        200: {"description": "Login successful, token returned", "model": Token},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password JSON body."""
    clean_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(clean_email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, role=_get_role_str(user.role))
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Form Login (Swagger UI compatibility)",
    description="OAuth2 password form login endpoint for Swagger UI Authorize dialog (uses 'username' field for email).",
    include_in_schema=True,
    responses={
        200: {"description": "Token granted", "model": Token},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
    },
)
def oauth2_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Authenticate using OAuth2 form-urlencoded credentials."""
    clean_email = form_data.username.strip().lower()
    user = db.query(User).filter(
        (User.email.ilike(clean_email)) | (User.username.ilike(clean_email))
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, role=_get_role_str(user.role))
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current user profile",
    description="Fetch the authenticated user's account details and assigned role.",
    responses={
        200: {"description": "Profile data retrieved", "model": UserResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update profile details",
    description="Update username, email, or change account password (requires current password verification).",
    responses={
        200: {"description": "Profile updated successfully", "model": UserResponse},
        400: {"description": "Invalid input, duplicate username/email, or incorrect current password", "model": ErrorResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update profile information or password for the current user."""
    if payload.username and payload.username.strip() != current_user.username:
        new_username = payload.username.strip()
        existing = db.query(User).filter(User.username.ilike(new_username), User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken")
        current_user.username = new_username

    if payload.email and payload.email.strip().lower() != current_user.email.lower():
        new_email = payload.email.strip().lower()
        existing = db.query(User).filter(User.email.ilike(new_email), User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
        current_user.email = new_email

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password",
            )
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        current_user.hashed_password = hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)

    log_activity(
        db,
        user_id=current_user.id,
        action="Profile Updated",
        details=f"User '{current_user.username}' updated profile settings",
    )
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User Logout",
    description="Stateless logout notification. Client should remove the JWT token from local storage.",
    responses={
        200: {"description": "Logged out successfully", "model": MessageResponse},
    },
)
def logout(current_user: User = Depends(get_current_user)):
    """Perform client-side logout cleanup."""
    return MessageResponse(message="Successfully logged out.")

"""
Authentication endpoints for user registration, login, and profile management.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_active_user, get_db
from app.models.database import User
from app.models.schemas import Token, UserCreate, UserLogin, UserResponse
from app.services.auth import AuthService


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    Args:
        user_data: User registration data (email, password, full_name)
        db: Database session

    Returns:
        Created user information (without password)

    Raises:
        HTTPException 400: If user with email already exists
    """
    try:
        user = AuthService.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password to get access token.

    Uses OAuth2 password flow (username field contains email).

    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException 401: If authentication fails
    """
    # Authenticate user (username field contains email)
    user = AuthService.authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    AuthService.update_last_login(db, user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
async def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with JSON payload (alternative to OAuth2 form).

    Args:
        credentials: Login credentials (email and password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException 401: If authentication fails
    """
    user = AuthService.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    AuthService.update_last_login(db, user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Current authenticated user (from token)

    Returns:
        Current user information
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout current user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint is provided for consistency
    and could be extended to maintain a token blacklist if needed.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return {"message": "Successfully logged out"}

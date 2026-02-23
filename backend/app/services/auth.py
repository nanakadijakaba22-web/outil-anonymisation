"""
Authentication service for user management and JWT handling.

Implements secure password hashing and JWT token generation/validation
compliant with Quebec Law 25 security requirements.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import User
from app.models.schemas import TokenData


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication and authorization operations."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Data to encode in the token (usually user_id and email)
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # Default expiration: 30 minutes
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[TokenData]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData object if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            email: str = payload.get("sub")
            user_id_str: str = payload.get("user_id")

            if email is None or user_id_str is None:
                return None

            user_id = UUID(user_id_str)
            return TokenData(email=email, user_id=user_id)

        except JWTError:
            return None
        except ValueError:  # Invalid UUID
            return None

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            db: Database session
            email: User email address

        Returns:
            User object if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            User object if found, None otherwise
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = AuthService.get_user_by_email(db, email)

        if not user:
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def create_user(db: Session, email: str, password: str, full_name: Optional[str] = None) -> User:
        """
        Create a new user account.

        Args:
            db: Database session
            email: User email
            password: Plain text password (will be hashed)
            full_name: Optional user full name

        Returns:
            Created User object

        Raises:
            ValueError: If user with email already exists
        """
        # Check if user already exists
        existing_user = AuthService.get_user_by_email(db, email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # Hash password
        hashed_password = AuthService.get_password_hash(password)

        # Create user
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_superuser=False
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """
        Update user's last login timestamp.

        Args:
            db: Database session
            user: User object
        """
        user.last_login = datetime.now(timezone.utc)
        db.commit()

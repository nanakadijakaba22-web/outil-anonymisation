"""
Tests for authentication endpoints and functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.services.auth import AuthService


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

    # Close all connections
    engine.dispose()


class TestAuthService:
    """Test authentication service functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "Test1234"
        hashed = AuthService.get_password_hash(password)

        # Hash should be different from plain password
        assert hashed != password

        # Should verify correctly
        assert AuthService.verify_password(password, hashed)

        # Should not verify incorrect password
        assert not AuthService.verify_password("WrongPassword", hashed)

    def test_jwt_token_creation_and_decoding(self):
        """Test JWT token creation and decoding."""
        import uuid

        user_id = uuid.uuid4()
        email = "test@example.com"

        # Create token
        token = AuthService.create_access_token(
            data={"sub": email, "user_id": str(user_id)}
        )

        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode token
        token_data = AuthService.decode_access_token(token)

        # Should decode correctly
        assert token_data is not None
        assert token_data.email == email
        assert token_data.user_id == user_id

    def test_invalid_token_decoding(self):
        """Test decoding of invalid token."""
        invalid_token = "invalid.token.here"
        token_data = AuthService.decode_access_token(invalid_token)

        # Should return None for invalid token
        assert token_data is None


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_register_user(self):
        """Test user registration endpoint."""
        import uuid
        unique_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "SecurePass123",
                "full_name": "New User"
            }
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        data = response.json()

        assert data["email"] == unique_email
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    def test_register_duplicate_email(self):
        """Test registration with duplicate email fails."""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Pass1234",  # Minimum 8 chars
            }
        )

        # Try to register same email again
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Pass5678",
            }
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_login_success(self):
        """Test successful login."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "loginuser@example.com",
                "password": "LoginPass123",
            }
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "loginuser@example.com",  # OAuth2 uses 'username' field
                "password": "LoginPass123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self):
        """Test login with wrong password fails."""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "CorrectPass123",
            }
        )

        # Try to login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@example.com",
                "password": "WrongPassword"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123"
            }
        )

        assert response.status_code == 401

    def test_get_current_user(self):
        """Test getting current user information."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "currentuser@example.com",
                "password": "UserPass123",
                "full_name": "Current User"
            }
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "currentuser@example.com",
                "password": "UserPass123"
            }
        )

        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "currentuser@example.com"
        assert data["full_name"] == "Current User"
        assert "last_login" in data

    def test_get_current_user_without_token(self):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self):
        """Test accessing protected endpoint with invalid token fails."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401

    def test_logout(self):
        """Test logout endpoint."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "logoutuser@example.com",
                "password": "LogoutPass123",
            }
        )

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "logoutuser@example.com",
                "password": "LogoutPass123"
            }
        )

        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "message" in response.json()

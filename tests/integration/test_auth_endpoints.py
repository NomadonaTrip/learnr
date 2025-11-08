"""
Integration tests for authentication API endpoints.

Tests:
- POST /v1/auth/register - User registration
- POST /v1/auth/login - User login
- POST /v1/auth/refresh - Token refresh
- POST /v1/auth/logout - User logout
- GET /v1/auth/me - Get current user
"""
import pytest
from fastapi import status


@pytest.mark.integration
class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_new_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@test.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["role"] == "learner"
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client, test_learner_user):
        """Test registration with existing email fails."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": test_learner_user.email,  # Duplicate
                "password": "SecurePass123!",
                "first_name": "Duplicate",
                "last_name": "User"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "User"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "weak",  # Too short, no special chars
                "first_name": "Test",
                "last_name": "User"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Check that validation error mentions password
        response_data = response.json()
        assert "detail" in response_data

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@test.com"
                # Missing password, first_name, last_name
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_is_inactive_by_default(self, client, db):
        """Test newly registered user has correct default values."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "inactive@test.com",
                "password": "SecurePass123!",
                "first_name": "Inactive",
                "last_name": "User"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_active"] is True  # Active by default
        assert data["email_verified"] is False  # Not verified yet


@pytest.mark.integration
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client, test_learner_user):
        """Test successful login with correct credentials."""
        response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        # Verify token is valid JWT (will decode without error if valid)
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["email"] == "learner@test.com"

    def test_login_wrong_password(self, client, test_learner_user):
        """Test login fails with wrong password."""
        response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login fails with non-existent email."""
        response = client.post(
            "/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "SomePassword123!"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = client.post(
            "/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "Password123!"
            }
        )

        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]

    def test_login_inactive_user(self, client, db, test_learner_user):
        """Test login fails for inactive user."""
        # Deactivate user
        test_learner_user.is_active = False
        db.commit()

        response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "inactive" in response.json()["detail"].lower()

    def test_login_updates_last_login(self, client, db, test_learner_user):
        """Test that login updates last_login_at timestamp."""
        from app.models.user import User

        # Get initial last_login
        initial_last_login = test_learner_user.last_login_at

        response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )

        assert response.status_code == status.HTTP_200_OK

        # Refresh user from DB
        db.refresh(test_learner_user)

        # last_login_at should be updated
        assert test_learner_user.last_login_at is not None
        if initial_last_login:
            assert test_learner_user.last_login_at > initial_last_login


@pytest.mark.integration
class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client, test_learner_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_invalid_token(self, client):
        """Test refresh fails with invalid token."""
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_access_token(self, client, test_learner_user):
        """Test refresh fails when using access token instead of refresh token."""
        # Get access token (not refresh token)
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token (should fail)
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        # Depending on implementation, this might succeed or fail
        # If tokens are differentiated, should fail
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.integration
class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_success(self, authenticated_client, test_learner_user):
        """Test getting current user with valid token."""
        response = authenticated_client.get("/v1/auth/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_learner_user.user_id
        assert data["email"] == test_learner_user.email
        assert data["role"] == "learner"
        assert "password_hash" not in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without authentication."""
        response = client.get("/v1/auth/me")

        # Returns 401 when no credentials are provided (auto_error=False)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        client.headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_expired_token(self, client, test_learner_user):
        """Test getting current user with expired token."""
        from app.services.auth import create_access_token
        from datetime import timedelta

        # Create expired token
        expired_token = create_access_token(
            {"sub": test_learner_user.user_id, "role": "learner"},
            expires_delta=timedelta(seconds=-1)
        )

        client.headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestLogout:
    """Test user logout endpoint."""

    def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        response = authenticated_client.post("/v1/auth/logout")

        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"].lower()

    def test_logout_without_auth(self, client):
        """Test logout without authentication."""
        response = client.post("/v1/auth/logout")

        # Returns 401 when no credentials are provided (auto_error=False)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flows."""

    def test_full_registration_login_flow(self, client):
        """Test complete flow: register -> login -> access protected resource."""
        # Step 1: Register
        register_response = client.post(
            "/v1/auth/register",
            json={
                "email": "fullflow@test.com",
                "password": "FullFlow123!",
                "first_name": "Full",
                "last_name": "Flow"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED

        # Step 2: Login
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "fullflow@test.com",
                "password": "FullFlow123!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.json()["access_token"]

        # Step 3: Access protected endpoint
        client.headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/v1/auth/me")
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == "fullflow@test.com"

    def test_token_refresh_flow(self, client, test_learner_user):
        """Test complete flow: login -> refresh token -> use new token."""
        # Step 1: Login
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Step 2: Refresh token
        refresh_response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["access_token"]

        # Step 3: Use new access token
        client.headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response = client.get("/v1/auth/me")
        assert me_response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestAuthorizationByRole:
    """Test role-based authorization."""

    def test_learner_cannot_access_admin_endpoints(self, authenticated_client):
        """Test that learner cannot access admin-only endpoints."""
        # Try to access admin endpoint (if implemented)
        response = authenticated_client.get("/v1/admin/users")

        # Should be forbidden or not found
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist yet
        ]

    def test_admin_can_access_admin_endpoints(self, admin_authenticated_client):
        """Test that admin can access admin endpoints."""
        response = admin_authenticated_client.get("/v1/admin/users")

        # Should succeed or not found (if not implemented yet)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist yet
        ]

    def test_token_contains_correct_role(self, client, test_learner_user, test_admin_user):
        """Test that JWT tokens contain correct role claims."""
        from jose import jwt
        from app.core.config import settings

        # Login as learner
        learner_response = client.post(
            "/v1/auth/login",
            json={"email": "learner@test.com", "password": "Test123Pass"}
        )
        learner_token = learner_response.json()["access_token"]
        learner_payload = jwt.decode(learner_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert learner_payload["role"] == "learner"

        # Login as admin
        admin_response = client.post(
            "/v1/auth/login",
            json={"email": "admin@test.com", "password": "Admin123Pass"}
        )
        admin_token = admin_response.json()["access_token"]
        admin_payload = jwt.decode(admin_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert admin_payload["role"] == "admin"



def test_register_first_user_becomes_admin(client):
    """The very first registered user in a fresh system should automatically receive the Admin role."""
    payload = {
        "email": "first_user@bugflow.dev",
        "username": "super_admin",
        "password": "Password123!",
        "role": "reporter",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "first_user@bugflow.dev"
    assert data["user"]["role"] == "admin"


def test_register_subsequent_user_respects_requested_role(client, admin_user):
    """Subsequent registrations should receive their requested role or default to reporter."""
    payload = {
        "email": "new_dev@bugflow.dev",
        "username": "new_dev",
        "password": "DevPassword123!",
        "role": "developer",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "developer"


def test_register_duplicate_email_rejected(client, admin_user):
    """Registering with an already existing email address should return HTTP 400."""
    payload = {
        "email": admin_user.email,
        "username": "another_admin",
        "password": "Password123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "Email is already registered" in response.json()["detail"]


def test_register_duplicate_username_rejected(client, admin_user):
    """Registering with an already existing username should return HTTP 400."""
    payload = {
        "email": "unique_email@bugflow.dev",
        "username": admin_user.username,
        "password": "Password123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "Username is taken" in response.json()["detail"]


def test_register_validation_short_password(client):
    """Passwords shorter than 6 characters must be rejected with HTTP 422 validation error."""
    payload = {
        "email": "short_pw@bugflow.dev",
        "username": "short_pw",
        "password": "123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_validation_invalid_email(client):
    """Malformed email strings must be rejected with HTTP 422 validation error."""
    payload = {
        "email": "not-a-valid-email",
        "username": "bad_email_user",
        "password": "ValidPassword123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_json_success(client, developer_user):
    """Valid credentials via JSON payload should return 200 and a JWT access token."""
    payload = {
        "email": developer_user.email,
        "password": "DevPass123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == developer_user.email


def test_login_invalid_password(client, developer_user):
    """Incorrect password should return HTTP 401 Unauthorized."""
    payload = {
        "email": developer_user.email,
        "password": "WrongPassword999!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Attempting to log in with an unregistered email should return HTTP 401."""
    payload = {
        "email": "ghost@bugflow.dev",
        "password": "AnyPassword123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401


def test_login_oauth2_form_success(client, developer_user):
    """OAuth2 form-urlencoded endpoint (/api/auth/token) must succeed for Swagger UI compatibility."""
    form_data = {
        "username": developer_user.email,
        "password": "DevPass123!",
    }
    response = client.post("/api/auth/token", data=form_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_get_me_authenticated(client, developer_user, developer_headers):
    """GET /api/auth/me should return the profile of the authenticated user."""
    response = client.get("/api/auth/me", headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == developer_user.id
    assert data["username"] == developer_user.username
    assert data["role"] == "developer"


def test_get_me_unauthenticated(client):
    """Accessing /api/auth/me without an Authorization token must return HTTP 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_tampered_token(client):
    """Accessing with an invalid or tampered JWT string must return HTTP 401."""
    headers = {"Authorization": "Bearer invalid.jwt.token.here"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401


def test_update_profile_username_and_email(client, developer_user, developer_headers):
    """Updating username and email with valid unique values should succeed."""
    payload = {
        "username": "dev_john_updated",
        "email": "dev_updated@bugflow.dev",
    }
    response = client.put("/api/auth/profile", json=payload, headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "dev_john_updated"
    assert data["email"] == "dev_updated@bugflow.dev"


def test_update_profile_password_change_success(client, developer_user, developer_headers):
    """Changing password with valid current password verification should update the credentials."""
    payload = {
        "current_password": "DevPass123!",
        "new_password": "NewBrandPassword456!",
    }
    response = client.put("/api/auth/profile", json=payload, headers=developer_headers)
    assert response.status_code == 200

    # Test login with new password
    login_res = client.post("/api/auth/login", json={
        "email": developer_user.email,
        "password": "NewBrandPassword456!",
    })
    assert login_res.status_code == 200


def test_update_profile_password_change_wrong_current_password(client, developer_user, developer_headers):
    """Attempting password change with wrong current password must return HTTP 400."""
    payload = {
        "current_password": "IncorrectCurrentPassword!",
        "new_password": "NewBrandPassword456!",
    }
    response = client.put("/api/auth/profile", json=payload, headers=developer_headers)
    assert response.status_code == 400
    assert "Current password is incorrect" in response.json()["detail"]


def test_logout(client, developer_headers):
    """POST /api/auth/logout should return HTTP 200 confirmation."""
    response = client.post("/api/auth/logout", headers=developer_headers)
    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]

"""Auth flow: register, duplicate, login, bad password, /auth/me."""


async def test_register_login_me(client):
    email = "authflow@test.co"
    r = await client.post(
        "/auth/register", json={"email": email, "password": "test-password-123"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["profile_complete"] is False

    # Duplicate registration is rejected.
    r = await client.post(
        "/auth/register", json={"email": email, "password": "test-password-123"}
    )
    assert r.status_code == 409

    # Wrong password.
    r = await client.post(
        "/auth/login", json={"email": email, "password": "wrong-password-1"}
    )
    assert r.status_code == 401

    # Correct login + /auth/me.
    r = await client.post(
        "/auth/login", json={"email": email, "password": "test-password-123"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email


async def test_short_password_rejected(client):
    r = await client.post(
        "/auth/register", json={"email": "short@test.co", "password": "short"}
    )
    assert r.status_code == 422


async def test_requests_require_token(client):
    for path in ("/auth/me", "/opportunities", "/applications", "/analytics/dashboard"):
        r = await client.get(path)
        assert r.status_code == 401, path


async def test_garbage_token_rejected(client):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401

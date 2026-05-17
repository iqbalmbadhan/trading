"""Phase 2: auth flow integration tests."""

import pyotp


def _register(client, email="trader@example.com", password="supersecret1"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def test_register_and_login(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "trader@example.com"
    assert body["totp_enabled"] is False

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]


def test_duplicate_registration_rejected(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 409


def test_login_wrong_password(client):
    _register(client)
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "nope"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    _register(client)
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "supersecret1"},
    ).json()
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "trader@example.com"


def test_refresh_rotates_tokens(client):
    _register(client)
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "supersecret1"},
    ).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_tokens = r.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # An access token cannot be used to refresh.
    bad = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


def test_2fa_setup_verify_and_enforced_login(client):
    _register(client)
    access = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access}"}

    setup = client.post("/api/v1/auth/2fa-setup", headers=auth_header)
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    # Wrong code is rejected; correct code enables 2FA.
    assert (
        client.post(
            "/api/v1/auth/2fa-verify", json={"code": "000000"}, headers=auth_header
        ).status_code
        == 401
    )
    code = pyotp.TOTP(secret).now()
    verified = client.post("/api/v1/auth/2fa-verify", json={"code": code}, headers=auth_header)
    assert verified.status_code == 200
    assert verified.json()["totp_enabled"] is True

    # Login now requires a valid TOTP code.
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "trader@example.com", "password": "supersecret1"},
        ).status_code
        == 401
    )
    ok = client.post(
        "/api/v1/auth/login",
        json={
            "email": "trader@example.com",
            "password": "supersecret1",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert ok.status_code == 200

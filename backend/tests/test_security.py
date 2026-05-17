"""Phase 2: security primitive unit tests."""

import time

import jwt
import pytest

from app.core import security


def test_password_hash_roundtrip():
    h = security.hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert security.verify_password("correct horse battery staple", h)
    assert not security.verify_password("wrong", h)


def test_access_and_refresh_tokens_have_correct_type():
    access = security.create_access_token("42")
    refresh = security.create_refresh_token("42")

    a = security.decode_token(access, expected_type="access")
    r = security.decode_token(refresh, expected_type="refresh")
    assert a["sub"] == "42"
    assert r["sub"] == "42"
    assert a["jti"] != r["jti"]


def test_wrong_token_type_rejected():
    access = security.create_access_token("1")
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(access, expected_type="refresh")


def test_expired_token_rejected():
    token = security.create_access_token("1")
    secret = security.get_settings().jwt_secret
    payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
    payload["exp"] = int(time.time()) - 10
    expired = jwt.encode(payload, secret, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(expired, expected_type="access")


def test_totp_verify():
    import pyotp

    secret = security.generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert security.verify_totp(secret, code)
    assert not security.verify_totp(secret, "000000")
    uri = security.totp_provisioning_uri(secret, "user@example.com")
    assert uri.startswith("otpauth://totp/")

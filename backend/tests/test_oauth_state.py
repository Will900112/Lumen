"""Tests for the OAuth CSRF state token (generate + verify)."""

import time

import jwt
import pytest
from fastapi import HTTPException

import main


def test_valid_state_roundtrip():
    state = main._generate_state()
    main._verify_state(state)  # must not raise


def test_tampered_state_is_rejected():
    state = main._generate_state()
    with pytest.raises(HTTPException) as exc:
        main._verify_state(state[:-4] + "XXXX")
    assert exc.value.status_code == 400


def test_expired_state_is_rejected():
    payload = {
        "csrf": "irrelevant",
        "exp": int(time.time()) - 10,
        "aud": "lumen:oauth-state",
    }
    expired = jwt.encode(payload, main.SECRET, algorithm="HS256")
    with pytest.raises(HTTPException):
        main._verify_state(expired)


def test_wrong_audience_is_rejected():
    payload = {
        "csrf": "irrelevant",
        "exp": int(time.time()) + 600,
        "aud": "some-other-app",
    }
    foreign = jwt.encode(payload, main.SECRET, algorithm="HS256")
    with pytest.raises(HTTPException):
        main._verify_state(foreign)


def test_state_signed_with_other_secret_is_rejected():
    payload = {
        "csrf": "irrelevant",
        "exp": int(time.time()) + 600,
        "aud": "lumen:oauth-state",
    }
    forged = jwt.encode(payload, "attacker-secret", algorithm="HS256")
    with pytest.raises(HTTPException):
        main._verify_state(forged)

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

import hashlib
import hmac
import base64
import json
import time
import random
import re
import os

JWT_SECRET  = os.getenv("JWT_SECRET", "debugai-jwt-secret-change-in-production-2024")
JWT_EXPIRY  = int(os.getenv("JWT_EXPIRY_HOURS", "24")) * 3600
OTP_EXPIRY  = 600  # 10 minutes


# ── Password hashing (pbkdf2 — stdlib only) ───────────────────────────────────

def hash_password(password: str) -> str:
    salt = base64.b64encode(os.urandom(16)).decode()
    dk   = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, stored_hash = stored.split("$", 1)
        dk       = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        computed = base64.b64encode(dk).decode()
        return hmac.compare_digest(computed, stored_hash)
    except Exception:
        return False


# ── JWT (stdlib hmac only) ────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def create_jwt(user_id: int, username: str) -> str:
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub":      user_id,
        "username": username,
        "iat":      int(time.time()),
        "exp":      int(time.time()) + JWT_EXPIRY,
    }).encode())
    sig_input = f"{header}.{payload}".encode()
    sig       = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url_encode(sig)}"


def verify_jwt(token: str) -> dict | None:
    try:
        header, payload, signature = token.strip().split(".")
        sig_input    = f"{header}.{payload}".encode()
        expected_sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), signature):
            return None
        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp() -> str:
    return str(random.randint(100_000, 999_999))


def otp_expires_at() -> int:
    return int(time.time()) + OTP_EXPIRY


def is_otp_valid(stored_otp: dict, submitted_code: str) -> tuple[bool, str]:
    if not stored_otp:
        return False, "No OTP found. Please request a new one."
    if stored_otp.get("used"):
        return False, "This OTP has already been used."
    if int(time.time()) > stored_otp.get("expires_at", 0):
        return False, "OTP has expired. Please request a new one."
    if not hmac.compare_digest(str(stored_otp["code"]), str(submitted_code).strip()):
        return False, "Incorrect OTP code."
    return True, "OTP verified."


# ── Input validation ──────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$", email))


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must have at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must have at least one number."
    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 30:
        return False, "Username must be 30 characters or less."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores."
    return True, ""
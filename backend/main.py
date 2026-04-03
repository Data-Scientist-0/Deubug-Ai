import sys
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from .database import (
    init_db, create_user, get_user_by_email, get_user_by_username,
    get_user_by_id, verify_user_email, update_username, update_password,
    delete_user, save_otp, get_latest_otp, mark_otp_used,
    create_session, get_sessions, get_session_by_id,
    update_session, delete_session, delete_all_sessions, get_session_stats,
)
from .auth import (
    hash_password, verify_password, create_jwt, verify_jwt,
    generate_otp, otp_expires_at, is_otp_valid,
    validate_email, validate_password, validate_username,
)
from .email_service import send_otp_email
from .models import (
    RegisterRequest, VerifyOTPRequest, ResendOTPRequest, LoginRequest,
    UpdateUsernameRequest, UpdatePasswordRequest,
    CreateSessionRequest, UpdateSessionRequest,
    TokenResponse, MessageResponse, UserResponse,
    SessionResponse, SessionDetailResponse, StatsResponse,
)

app = FastAPI(
    title="DebugAI API",
    description="AI/ML Code Debugging Agent — FastAPI Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

security = HTTPBearer()


def send_email_background(email: str, username: str, otp: str):
    """Send email in background thread — non blocking."""
    try:
        send_otp_email(email, username, otp)
    except Exception:
        pass


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    data  = verify_jwt(token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
        )
    user = get_user_by_id(data["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Email not verified.")
    return user


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=MessageResponse)
def register(body: RegisterRequest, background_tasks: BackgroundTasks):
    ok, msg = validate_username(body.username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    if not validate_email(body.email):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    ok, msg = validate_password(body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    if get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already taken.")
    if get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    hashed = hash_password(body.password)
    user   = create_user(body.username, body.email, hashed)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create account.")

    otp = generate_otp()
    exp = otp_expires_at()
    save_otp(body.email, otp, exp)

    # Send email in background — API responds instantly
    background_tasks.add_task(send_email_background, body.email, body.username, otp)

    return MessageResponse(
        message=f"Account created! A 6-digit verification code is being sent to {body.email}. Check your inbox in a few seconds.",
        success=True,
    )


@app.post("/auth/verify-otp", response_model=MessageResponse)
def verify_otp(body: VerifyOTPRequest):
    user = get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    if user["is_verified"]:
        return MessageResponse(message="Email already verified. You can log in.", success=True)
    stored = get_latest_otp(body.email)
    valid, msg = is_otp_valid(stored, body.otp)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)
    verify_user_email(body.email)
    mark_otp_used(body.email)
    return MessageResponse(message="Email verified! You can now log in.", success=True)


@app.post("/auth/resend-otp", response_model=MessageResponse)
def resend_otp(body: ResendOTPRequest, background_tasks: BackgroundTasks):
    user = get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    if user["is_verified"]:
        return MessageResponse(message="Email already verified.", success=True)
    otp = generate_otp()
    exp = otp_expires_at()
    save_otp(body.email, otp, exp)
    background_tasks.add_task(send_email_background, body.email, user["username"], otp)
    return MessageResponse(message=f"New verification code is being sent to {body.email}", success=True)


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = get_user_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Username not found.")
    if not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox for the verification code.",
        )
    token = create_jwt(user["id"], user["username"])
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        user_id=user["id"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# USER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/users/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        is_verified=bool(current_user["is_verified"]),
        created_at=current_user["created_at"],
    )


@app.put("/users/me", response_model=MessageResponse)
def update_me(body: UpdateUsernameRequest, current_user: dict = Depends(get_current_user)):
    ok, msg = validate_username(body.username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    updated = update_username(current_user["id"], body.username)
    if not updated:
        raise HTTPException(status_code=409, detail="Username already taken.")
    return MessageResponse(message="Username updated successfully.", success=True)


@app.put("/users/me/password", response_model=MessageResponse)
def change_password(body: UpdatePasswordRequest, current_user: dict = Depends(get_current_user)):
    if not verify_password(body.old_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    ok, msg = validate_password(body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    update_password(current_user["id"], hash_password(body.new_password))
    return MessageResponse(message="Password changed successfully.", success=True)


@app.delete("/users/me", response_model=MessageResponse)
def delete_me(current_user: dict = Depends(get_current_user)):
    delete_user(current_user["id"])
    return MessageResponse(message="Account deleted successfully.", success=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/sessions/stats", response_model=StatsResponse)
def session_stats(current_user: dict = Depends(get_current_user)):
    stats = get_session_stats(current_user["id"])
    return StatsResponse(
        total_sessions=stats.get("total", 0),
        total_bugs=stats.get("total_bugs", 0),
        last_session=stats.get("last_session"),
    )


@app.get("/sessions", response_model=list[SessionResponse])
def list_sessions(current_user: dict = Depends(get_current_user)):
    rows = get_sessions(current_user["id"])
    return [SessionResponse(**r) for r in rows]


@app.post("/sessions", response_model=SessionDetailResponse)
def new_session(body: CreateSessionRequest, current_user: dict = Depends(get_current_user)):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    row = create_session(
        current_user["id"], body.title, body.stack,
        body.code, body.result, body.bug_count,
    )
    return SessionDetailResponse(**row)


@app.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, current_user: dict = Depends(get_current_user)):
    row = get_session_by_id(session_id, current_user["id"])
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionDetailResponse(**row)


@app.put("/sessions/{session_id}", response_model=MessageResponse)
def rename_session(session_id: int, body: UpdateSessionRequest, current_user: dict = Depends(get_current_user)):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    ok = update_session(session_id, current_user["id"], body.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found.")
    return MessageResponse(message="Session renamed.", success=True)


@app.delete("/sessions/all", response_model=MessageResponse)
def clear_sessions(current_user: dict = Depends(get_current_user)):
    delete_all_sessions(current_user["id"])
    return MessageResponse(message="All sessions deleted.", success=True)


@app.delete("/sessions/{session_id}", response_model=MessageResponse)
def remove_session(session_id: int, current_user: dict = Depends(get_current_user)):
    ok = delete_session(session_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found.")
    return MessageResponse(message="Session deleted.", success=True)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": "DebugAI API", "version": "1.0.0"}


# ── Debug env check ───────────────────────────────────────────────────────────
@app.get("/debug/env")
def debug_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    return {
        "env_file_path":      str(env_path),
        "env_file_exists":    env_path.exists(),
        "GMAIL_USER":         os.getenv("GMAIL_USER", "NOT SET"),
        "GMAIL_APP_PASSWORD": "SET ✅" if os.getenv("GMAIL_APP_PASSWORD") else "NOT SET ❌",
        "GEMINI_API_KEY":     "SET ✅" if os.getenv("GEMINI_API_KEY") else "NOT SET ❌",
        "JWT_SECRET":         "SET ✅" if os.getenv("JWT_SECRET") else "NOT SET ❌",
    }

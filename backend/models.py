from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


class ResendOTPRequest(BaseModel):
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateUsernameRequest(BaseModel):
    username: str


class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateSessionRequest(BaseModel):
    title: str
    stack: str
    code: str
    result: str
    bug_count: int


class UpdateSessionRequest(BaseModel):
    title: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class MessageResponse(BaseModel):
    message: str
    success: bool


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_verified: bool
    created_at: str


class SessionResponse(BaseModel):
    id: int
    title: str
    stack: str
    bug_count: int
    created_at: str
    updated_at: str


class SessionDetailResponse(BaseModel):
    id: int
    title: str
    stack: str
    code: str
    result: str
    bug_count: int
    created_at: str
    updated_at: str


class StatsResponse(BaseModel):
    total_sessions: int
    total_bugs: int
    last_session: Optional[str]
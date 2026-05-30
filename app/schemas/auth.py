from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    ok: bool = True
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LoginErrorResponse(BaseModel):
    ok: bool = False
    error: str


class MeResponse(BaseModel):
    user: UserPublic


class ChangePasswordRequest(BaseModel):
    currentPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=6, max_length=255)


class ChangePasswordResponse(BaseModel):
    ok: bool = True
    user: UserPublic

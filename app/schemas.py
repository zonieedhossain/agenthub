from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    sub_agent_id: Optional[int] = None

class ChatResponse(BaseModel):
    reply: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


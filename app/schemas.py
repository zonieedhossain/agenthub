from typing import Optional
from pydantic import BaseModel, EmailStr


# --- Auth ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Chat ---

class ChatRequest(BaseModel):
    message: str
    sub_agent_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str


# --- Admin ---

class AdminSubAgentInput(BaseModel):
    name: str
    task: str


class AdminAgentInput(BaseModel):
    number: int
    industry: str
    profession: str
    sub_agents: list[AdminSubAgentInput]  # 2-5 items expected
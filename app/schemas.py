from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Auth ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # 72 = bcrypt's own input limit


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
    name: str = Field(min_length=3, max_length=80)
    task: str = Field(min_length=5, max_length=300)

    @field_validator("name", "task")
    @classmethod
    def strip_and_reject_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class AdminAgentInput(BaseModel):
    number: int = Field(gt=0)
    industry: str = Field(min_length=3, max_length=80)
    profession: str = Field(min_length=3, max_length=80)
    sub_agents: list[AdminSubAgentInput] = Field(max_length=5)  # 2-5 expected, hard cap 5

    @field_validator("industry", "profession")
    @classmethod
    def strip_and_reject_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v
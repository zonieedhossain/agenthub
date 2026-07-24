from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import SignupRequest, LoginRequest, TokenResponse
from app.auth import hash_password, verify_password, create_access_token
from app.models import Agent, User
from app.rate_limit import limiter

router = APIRouter()


# No authenticated user exists yet at signup/login, so the limiter's
# key_func falls back to per-IP (see app/rate_limit.py) — the right
# behavior here, unlike chat where per-user keying matters.
@router.post("/agents/{slug}/signup", response_model=TokenResponse)
@limiter.limit("10/minute")
def signup(request: Request, slug: str, body: SignupRequest, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    existing = db.query(User).filter_by(email=body.email, agent_id=agent.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for this email under this agent")

    user = User(email=body.email, password_hash=hash_password(body.password), agent_id=agent.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, agent_id=agent.id)
    return TokenResponse(access_token=token)


@router.post("/agents/{slug}/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, slug: str, body: LoginRequest, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    user = db.query(User).filter_by(email=body.email, agent_id=agent.id).first()
    # same generic error whether the email or password is wrong —
    # avoids revealing which emails are registered under this agent
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, agent_id=agent.id)
    return TokenResponse(access_token=token)
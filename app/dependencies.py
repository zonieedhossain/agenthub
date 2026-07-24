from fastapi import Depends, HTTPException, Header, Request
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import decode_access_token
from app.models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request, slug: str, authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.models import Agent
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # THE ISOLATION CHECK — a token from one agent must not work on another
    if payload["agent_id"] != agent.id:
        raise HTTPException(status_code=401, detail="Token not valid for this agent")

    user = db.query(User).filter_by(id=payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    request.state.user = user  # lets the rate limiter key by user instead of falling back to IP
    return user
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import Agent, SubAgent, Message, User, UsageLog
from app.schemas import ChatRequest, ChatResponse
from app.llm import get_reply

from app.rate_limit import limiter

router = APIRouter()

@router.get("/agents/{slug}/chat/history")
def get_chat_history(
        slug: str,
        sub_agent_id: int | None = None,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    query = (
        db.query(Message)
        .filter_by(user_id=current_user.id, agent_id=agent.id, sub_agent_id=sub_agent_id)
        .order_by(Message.created_at.desc())
    )
    total = query.count()
    rows = query.offset((page - 1) * limit).limit(limit).all()
    rows.reverse()

    return {
        "items": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }

@router.post("/agents/{slug}/chat", response_model=ChatResponse)
@limiter.limit("15/minute")
def chat(
        request: Request,
        slug: str,
        body: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    sub_agent = None
    system_prompt = agent.system_prompt
    if body.sub_agent_id:
        sub_agent = db.query(SubAgent).filter_by(id=body.sub_agent_id, agent_id=agent.id).first()
        if not sub_agent:
            raise HTTPException(status_code=404, detail="Sub-agent not found for this agent")
        system_prompt = sub_agent.system_prompt

    # load this conversation's most recent 20 messages (same user + agent + sub_agent),
    # capped to control LLM cost/context size on long-running conversations
    history_rows = (
        db.query(Message)
        .filter_by(user_id=current_user.id, agent_id=agent.id, sub_agent_id=sub_agent.id if sub_agent else None)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    history_rows.reverse()  # back to chronological order (oldest first)

    history = [{"role": m.role, "content": m.content} for m in history_rows]
    history.append({"role": "user", "content": body.message})

    reply = get_reply(system_prompt, history)

    db.add(Message(user_id=current_user.id, agent_id=agent.id,
                   sub_agent_id=sub_agent.id if sub_agent else None,
                   role="user", content=body.message))
    db.add(Message(user_id=current_user.id, agent_id=agent.id,
                   sub_agent_id=sub_agent.id if sub_agent else None,
                   role="assistant", content=reply))
    db.add(UsageLog(
        agent_id=agent.id,
        user_id=current_user.id,
        tokens=len(reply.split())  # rough word-count estimate; swap for real
        # token count if the LLM API returns one
    ))
    db.commit()

    return ChatResponse(reply=reply)
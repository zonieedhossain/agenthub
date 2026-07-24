from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import Agent, SubAgent, Message, User
from app.schemas import ChatRequest, ChatResponse
from app.llm import get_reply

router = APIRouter()


@router.post("/agents/{slug}/chat", response_model=ChatResponse)
def chat(
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

    # load this conversation's prior messages (same user + agent + sub_agent)
    history_rows = (
        db.query(Message)
        .filter_by(user_id=current_user.id, agent_id=agent.id, sub_agent_id=sub_agent.id if sub_agent else None)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]
    history.append({"role": "user", "content": body.message})

    reply = get_reply(system_prompt, history)

    db.add(Message(user_id=current_user.id, agent_id=agent.id,
                   sub_agent_id=sub_agent.id if sub_agent else None,
                   role="user", content=body.message))
    db.add(Message(user_id=current_user.id, agent_id=agent.id,
                   sub_agent_id=sub_agent.id if sub_agent else None,
                   role="assistant", content=reply))
    db.commit()

    return ChatResponse(reply=reply)
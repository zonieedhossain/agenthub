from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Agent, SubAgent

router = APIRouter()


@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).filter_by(is_active=1).order_by(Agent.number).all()
    return [
        {"slug": a.slug, "industry": a.industry, "profession": a.profession, "description": a.description}
        for a in agents
    ]


@router.get("/agents/{slug}")
def get_agent(slug: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    subs = db.query(SubAgent).filter_by(agent_id=agent.id).all()
    return {
        "slug": agent.slug,
        "industry": agent.industry,
        "profession": agent.profession,
        "description": agent.description,
        "sub_agents": [{"id": s.id, "slug": s.slug, "name": s.name, "task": s.task} for s in subs],
    }
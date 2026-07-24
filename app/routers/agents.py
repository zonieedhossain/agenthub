from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Agent, SubAgent

router = APIRouter()


@router.get("/agents")
def list_agents(
        page: int = Query(1, ge=1),
        limit: int = Query(18, ge=1, le=100),
        db: Session = Depends(get_db),
):
    query = db.query(Agent).filter_by(is_active=1).order_by(Agent.updated_at.desc(), Agent.number.asc())
    total = query.count()
    agents = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [
            {"slug": a.slug, "industry": a.industry, "profession": a.profession, "description": a.description}
            for a in agents
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/api/agents/{slug}")
def get_agent(slug: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter_by(slug=slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    subs = (
        db.query(SubAgent)
        .filter_by(agent_id=agent.id)
        .order_by(SubAgent.updated_at.desc(), SubAgent.id.asc())
        .all()
    )
    return {
        "slug": agent.slug,
        "industry": agent.industry,
        "profession": agent.profession,
        "description": agent.description,
        "sub_agents": [{"id": s.id, "slug": s.slug, "name": s.name, "task": s.task} for s in subs],
    }
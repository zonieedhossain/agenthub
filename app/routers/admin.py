from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.admin_auth import verify_admin
from app.models import Agent, UsageLog
from app.schemas import AdminAgentInput
from pipeline.ingest import upsert_agent

router = APIRouter()

@router.post("/admin/agents", dependencies=[Depends(verify_admin)])
def add_agent(body: AdminAgentInput, db: Session = Depends(get_db)):
    from pipeline.ingest import slugify

    slug = slugify(body.profession)
    is_update = db.query(Agent).filter_by(slug=slug).first() is not None

    subs_data = [(s.name, s.task) for s in body.sub_agents]
    agent = upsert_agent(db, body.number, body.industry, body.profession, subs_data)
    db.commit()

    verb = "updated" if is_update else "created"
    return {
        "slug": agent.slug,
        "created": not is_update,
        "message": f"Agent '{agent.profession}' {verb} with {len(subs_data)} sub-agents",
    }

@router.get("/admin/stats", dependencies=[Depends(verify_admin)])
def usage_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(Agent.profession, Agent.slug, func.count(UsageLog.id), func.sum(UsageLog.tokens))
        .join(UsageLog, UsageLog.agent_id == Agent.id)
        .group_by(Agent.profession, Agent.slug)
        .order_by(func.count(UsageLog.id).desc())
        .all()
    )
    return [
        {"agent": r[0], "slug": r[1], "requests": r[2], "tokens": int(r[3] or 0)}
        for r in rows
    ]


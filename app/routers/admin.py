from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.admin_auth import verify_admin
from app.schemas import AdminAgentInput
from pipeline.ingest import upsert_agent

router = APIRouter()

@router.post("/admin/agents", dependencies=[Depends(verify_admin)])
def add_agent(body: AdminAgentInput, db: Session = Depends(get_db)):
    subs_data = [(s.name, s.task) for s in body.sub_agents]
    agent = upsert_agent(db, body.number, body.industry, body.profession, subs_data)
    db.commit()
    return {"slug": agent.slug, "message": f"Agent '{agent.profession}' created/updated with {len(subs_data)} sub-agents"}

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


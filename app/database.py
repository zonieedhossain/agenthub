import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from app import models  # ensures models are registered before creating tables
    Base.metadata.create_all(bind=engine)
    _migrate_agent_timestamps()


def _migrate_agent_timestamps():
    """Additive, idempotent migration for DBs seeded before created_at/updated_at
    existed on agents/sub_agents. Adds the columns if missing, then backfills
    already-seeded rows with timestamps derived from their original order so they
    keep their relative position — only genuinely new/edited rows get a real
    "now" timestamp and sort above them. No-op once columns already exist
    (fresh DBs get them straight from create_all, with real server defaults)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    added_any = False
    for table in ("agents", "sub_agents"):
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        with engine.begin() as conn:
            for col in ("created_at", "updated_at"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} TIMESTAMP"))
                    added_any = True

    if added_any:
        _backfill_agent_timestamps()


def _backfill_agent_timestamps():
    from datetime import datetime
    from app.models import Agent, SubAgent

    # One shared timestamp for every pre-existing row, not one per row — they
    # need to *tie* so ORDER BY updated_at DESC falls back to the number/id
    # tiebreaker and preserves original order. A distinct timestamp per row
    # would instead sort backfilled rows by number descending, which isn't
    # "unordered", it's silently reversed.
    base = datetime(2020, 1, 1)

    session = SessionLocal()
    try:
        session.query(Agent).filter(Agent.created_at.is_(None)).update(
            {"created_at": base, "updated_at": base}, synchronize_session=False
        )
        session.query(SubAgent).filter(SubAgent.created_at.is_(None)).update(
            {"created_at": base, "updated_at": base}, synchronize_session=False
        )
        session.commit()
    finally:
        session.close()
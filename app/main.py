import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine, init_db
from app.routers.auth import router as auth_router
from app.routers.agents import router as agents_router
from app.routers.chat import router as chat_router
from pipeline.ingest import run as seed_agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful")
    except Exception as e:
        print("❌ Database connection failed:", e)
        sys.exit(1)

    init_db()  # make sure tables exist before seeding

    try:
        seed_agents("pipeline/agents_sample.xlsx")
    except Exception as e:
        print("Seeding failed (app will still start):", e)

    yield
    print("Shutting down AgentHub")


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"message": "AgentHub is alive"}
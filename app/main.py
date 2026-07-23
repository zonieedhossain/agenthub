import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: runs before the app starts accepting requests
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful")
    except Exception as e:
        print("Database connection failed:", e)
        print("Stopping app — check your DATABASE_URL in .env")
        sys.exit(1)

    # Auto-seed on every startup — safe because ingest.py is idempotent
    try:
        seed_agents("pipeline/agents_sample.xlsx")
    except Exception as e:
        print("Seeding failed (app will still start):", e)

    yield  # app runs here, serving requests

    # Shutdown: runs when the app is stopping (optional cleanup)
    print("Shutting down AgentHub")

app = FastAPI(lifespan=lifespan)

from app.routers.auth import router as auth_router

app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "AgentHub is alive"}
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine, init_db


from pipeline.ingest import run as seed_agents
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limit import limiter

from app.routers.auth import router as auth_router
from app.routers.agents import router as agents_router
from app.routers.chat import router as chat_router
from app.routers.admin import router as admin_router

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

templates = Jinja2Templates(directory="templates")

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(admin_router)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html", {})

@app.get("/")
def catalog_page(request: Request):
    return templates.TemplateResponse(request, "catalog.html", {})

@app.get("/agents/{slug}")
def agent_page(request: Request, slug: str):
    return templates.TemplateResponse(request, "agent_detail.html", {"slug": slug})

@app.get("/agents/{slug}/auth")
def auth_page(request: Request, slug: str):
    return templates.TemplateResponse(request, "auth.html", {"slug": slug})

@app.get("/agents/{slug}/chat")
def chat_page(request: Request, slug: str):
    return templates.TemplateResponse(request, "chat.html", {"slug": slug})


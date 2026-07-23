import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))  # let it import from app/

from app.database import SessionLocal, init_db
from app.models import Agent, SubAgent


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def repair_truncated_name(name: str, industry: str) -> str:
    if industry and industry not in name:
        for cut in range(len(industry) - 1, 5, -1):
            prefix = industry[:cut]
            if prefix in name:
                return name.replace(prefix, industry, 1)
    return name


MAIN_PROMPT = """You are the {profession} Agent on AgentHub, an AI assistant for \
{profession}s in the {industry} industry.

Your specialized capabilities (also available as dedicated sub-agents):
{capabilities}

Stay in character, be concise and practical. For regulated topics (medical, legal, \
financial), remind the user that final decisions require a licensed professional."""

SUB_PROMPT = """You are the {sub_name}, a specialized sub-agent of the {profession} Agent \
on AgentHub, serving {profession}s in the {industry} industry.

Your specialization: {sub_task}

Answer only from this specialization. Stay in character, be concise and practical."""


import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Agent, SubAgent


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def repair_truncated_name(name: str, industry: str) -> str:
    if industry and industry not in name:
        for cut in range(len(industry) - 1, 5, -1):
            prefix = industry[:cut]
            if prefix in name:
                return name.replace(prefix, industry, 1)
    return name


MAIN_PROMPT = """You are the {profession} Agent on AgentHub, an AI assistant for \
{profession}s in the {industry} industry.

Your specialized capabilities (also available as dedicated sub-agents):
{capabilities}

Stay in character, be concise and practical. For regulated topics (medical, legal, \
financial), remind the user that final decisions require a licensed professional."""

SUB_PROMPT = """You are the {sub_name}, a specialized sub-agent of the {profession} Agent \
on AgentHub, serving {profession}s in the {industry} industry.

Your specialization: {sub_task}

Answer only from this specialization. Stay in character, be concise and practical."""


def run(xlsx_path: str):
    df = pd.read_excel(xlsx_path)
    session = SessionLocal()

    try:
        for _, row in df.iterrows():
            industry = clean(row["Industry"])
            profession = clean(row["Profession"])
            slug = slugify(profession)

            subs_data = []
            for i in range(1, 5):
                name = clean(row[f"Agent {i}"])
                task = clean(row[f"Agent {i} Task"])
                if not name or not task:
                    continue
                name = repair_truncated_name(name, industry)
                subs_data.append((name, task))

            capabilities = "\n".join(f"- {n}: {t}" for n, t in subs_data)
            system_prompt = MAIN_PROMPT.format(profession=profession, industry=industry, capabilities=capabilities)

            agent = session.query(Agent).filter_by(slug=slug).first()
            if not agent:
                agent = Agent(slug=slug, number=int(row["#"]), industry=industry,
                              profession=profession, description=f"AI assistant for {profession}s in {industry}.",
                              system_prompt=system_prompt)
                session.add(agent)
                session.flush()
            else:
                agent.industry = industry
                agent.system_prompt = system_prompt

            for name, task in subs_data:
                sub_slug = slugify(name)
                sub = session.query(SubAgent).filter_by(agent_id=agent.id, slug=sub_slug).first()
                sub_prompt = SUB_PROMPT.format(sub_name=name, profession=profession, industry=industry, sub_task=task)
                if not sub:
                    session.add(SubAgent(agent_id=agent.id, slug=sub_slug, name=name, task=task, system_prompt=sub_prompt))
                else:
                    sub.task = task
                    sub.system_prompt = sub_prompt

        session.commit()
        count = session.query(Agent).count()
        sub_count = session.query(SubAgent).count()
        print(f"Seeded {count} agents, {sub_count} sub-agents")

    except Exception as e:
        session.rollback()   # undo any partial changes from this run
        print("Seeding failed, rolled back:", e)
        raise                # re-raise so the caller (e.g. app startup) knows it failed

    finally:
        session.close()      # ALWAYS runs — releases the DB connection either way


if __name__ == "__main__":
    init_db()
    run("pipeline/agents_sample.xlsx")

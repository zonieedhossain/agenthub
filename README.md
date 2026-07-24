# AgentHub

A "Play Store" for AI agents: browse a catalog of ~100 profession-specific AI agents (doctor, lawyer, accountant, software engineer, ...), sign in for the one agent you picked, and chat with it — powered by a real LLM (Gemini), in character.

**Live:** https://agenthub-hxt8.onrender.com/
*(hosted on Render's free tier — the instance spins down after ~15 minutes of inactivity, so the first request after a while can take 20–30s to wake up)*

## Test accounts

Login is scoped per agent (see [Auth design](#auth-design) below), so a token minted for one agent's account does not work on another agent. To verify isolation yourself, either sign up fresh under two different agents, or use:

| Agent | URL | Email | Password |
|---|---|---|---|
| Financial Controller | `/agents/financial-controller/auth` | `agenthub.demo@gmail.com` | `Demo12345!` |
| Chartered Accountant | `/agents/chartered-accountant/auth` | `agenthub.demo@gmail.com` | `Demo12345!` |

Same email, two separate accounts (one per agent) — the token from one will return `401` if used against the other's chat endpoint. Signup is open, so you can also just create your own account under any of the ~100 agents from the catalog.

## Architecture

### Agents are data, not code

There is exactly one `Agent` model and one `SubAgent` model (`app/models.py`). Every one of the ~100 catalog entries — and every sub-agent under them — is a row in those two tables, not a Python class or a code path. The chat endpoint (`app/routers/chat.py`) resolves whichever agent/sub-agent the request names and passes its `system_prompt` column straight to the LLM call. Adding agent #101 means adding a row (via the pipeline script or the `/admin/agents` endpoint below) — no new code, no redeploy.

### Content pipeline

`pipeline/ingest.py` turns raw agent data (originally `agents_sample.csv`, converted to `.xlsx` here) into working agent configs:

- `upsert_agent()` is the single function that generates a system prompt from a template (`MAIN_PROMPT`/`SUB_PROMPT`) given a profession, industry, and up to 4 sub-agent (name, task) pairs, then creates or updates the `Agent`/`SubAgent` rows.
- `run()` batch-imports the whole spreadsheet on app startup (see `lifespan` in `app/main.py` — it seeds the DB automatically the first time it connects).
- The **same** `upsert_agent()` function backs `POST /admin/agents`, so a single agent can be added or updated by hand through the admin UI with zero code changes — the CSV import and the admin form are two callers of one code path, not two implementations.

### Auth design

Each agent gets its own login boundary using a **shared auth system, tenant-scoped by `agent_id`** — not fully separate systems per agent. Concretely:

- `User` rows have a composite unique constraint on `(email, agent_id)` — the same email can sign up under multiple agents as *different* accounts.
- On signup/login, a JWT is issued with both `user_id` and `agent_id` embedded in the payload.
- Every authenticated request carries the agent's `slug` in the URL. `get_current_user` (`app/dependencies.py`) decodes the token and explicitly checks `payload["agent_id"] != agent.id` — a token minted for one agent is rejected outright on any other agent's endpoints, even though it's cryptographically valid.

**Why shared-and-scoped over fully separate systems:** with ~100 (and growing) agents, running fully independent auth stacks per agent doesn't scale operationally — every agent would need its own user table, its own secret, its own session store. A single `users` table with an `agent_id` column and an isolation check enforced at the dependency layer gives the same guarantee (one login literally cannot be used elsewhere) with one schema and one code path to secure and test. The tradeoff is that the isolation check lives in application code rather than being structurally impossible — which is why it's covered directly by tests (`tests/test_auth.py::test_token_from_one_agent_rejected_on_another`), not just assumed.

Passwords are hashed with bcrypt (`passlib`), never stored or logged in plaintext. `.env` (secrets) is gitignored and was never committed.

### Stack

- **Backend:** FastAPI + SQLAlchemy, Postgres in production (Neon free tier), SQLite for tests
- **Frontend:** Jinja2-rendered pages + vanilla JS (no build step, no framework) — kept deliberately minimal since the assignment's frontend framework choice was open and the surface area here (catalog, auth, chat, admin) didn't need one
- **LLM:** Google Gemini (`google-genai`, `gemini-flash-latest`)
- **Rate limiting:** `slowapi`, keyed by authenticated user (falls back to IP only for unauthenticated requests)
- **Deployment:** Render (`render.yaml`), free tier

## Setup

### Requirements
Python 3.11+, a Postgres database (or SQLite for local/dev), a Gemini API key.

### Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | e.g. `postgresql://...` or `sqlite:///./dev.db` |
| `JWT_SECRET` | Yes | any long random string |
| `GEMINI_API_KEY` | Yes | from Google AI Studio |
| `ADMIN_USER` / `ADMIN_PASSWORD` | Yes | gates the `/admin` UI and `/admin/*` API |

### Run locally

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# create a .env with the variables above

uvicorn app.main:app --reload
```

On first startup, the app connects to the DB, creates tables if needed, and seeds all ~100 agents from `pipeline/agents_sample.xlsx` automatically (see `lifespan` in `app/main.py`) — no manual migration step required. Visit `http://localhost:8000`.

### Run the content pipeline manually

```bash
python -m pipeline.ingest
```

Re-running it is idempotent — it upserts by slug, so it's safe to run again after editing the source spreadsheet.

### Tests

```bash
pytest tests/ -v
```

10 tests covering the auth flow (signup, login, duplicate emails, wrong password, and — the important one — cross-agent token isolation) and chat/config resolution (main-agent vs sub-agent system prompt resolution, and rejecting a sub-agent that belongs to a different agent). Tests run against an in-memory SQLite DB via dependency override, no external services required. CI (`.github/workflows/test.yml`) runs this suite on every push/PR to `main`.

## AI-assisted development

This project was built with **Claude Code** (Anthropic) as the primary coding assistant throughout — architecture, implementation, debugging, and this README were all done in collaboration with it, including a pass where it drove the deployed app in a real headless browser to find and fix bugs that unit tests alone hadn't caught (see commit history).

## Known limitations

- **No password strength requirement** on signup — any non-empty string is accepted. Would add a minimum length before production use.
- **Signup/login aren't rate-limited** — only the chat endpoint is. A determined attacker could brute-force a weak password since there's no lockout or throttling on `/agents/{slug}/login`.
- **Single shared admin credential** (`ADMIN_USER`/`ADMIN_PASSWORD`), not per-admin accounts — fine for a small team, not for a multi-admin org.
- **No HTTPS enforcement in application code** — relies on the hosting platform (Render) terminating TLS, which it does, but the app itself would happily serve plain HTTP if run elsewhere without a proxy in front.
- **Free-tier cold starts.** Render's free plan spins the instance down after inactivity; the first request afterward is slow. Not fixable without paid hosting.
- **`upsert_agent` doesn't remove sub-agents missing from a new submission.** Re-adding an agent through `/admin/agents` with a different sub-agent list accumulates rather than replaces — the old ones stay unless you also delete them.
- **Ad hoc schema migrations, no Alembic.** New columns (`created_at`/`updated_at`) get added to an already-seeded DB via a small guarded `ALTER TABLE` in `init_db()` rather than a real migration tool — fine at this scale, wouldn't scale to a team environment.

## What I'd do differently with more time

- Move the JSON API fully behind an `/api/*` prefix (started this — `GET /api/agents/{slug}` — but `GET /agents` (the list endpoint) is still unprefixed) so page routes and API routes can never collide again by construction, instead of by convention.
- Add refresh tokens / shorter-lived access tokens instead of a flat 24h JWT with no revocation.
- Stream LLM responses instead of waiting for the full completion — the UI currently blocks on the whole reply.
- Add structured logging/observability beyond the basic `UsageLog` table (request latency, error rates, per-agent cost tracking).
- Real integration tests against a Postgres test container instead of only SQLite, to catch Postgres-specific behavior differences.

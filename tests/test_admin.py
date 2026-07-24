from tests.conftest import admin_auth_header


def valid_agent_payload(profession="Test Profession", number=9001):
    return {
        "number": number,
        "industry": "Test Industry",
        "profession": profession,
        "sub_agents": [
            {"name": "First Sub-Agent", "task": "Does the first specialized thing"},
            {"name": "Second Sub-Agent", "task": "Does the second specialized thing"},
        ],
    }


def test_admin_endpoint_requires_auth(client):
    res = client.post("/admin/agents", json=valid_agent_payload())
    assert res.status_code == 401


def test_admin_rejects_wrong_credentials(client):
    bad_auth = {"Authorization": "Basic d3Jvbmc6Y3JlZHM="}  # wrong:creds
    res = client.get("/admin/stats", headers=bad_auth)
    assert res.status_code == 401


def test_admin_rejects_too_short_profession(client):
    payload = valid_agent_payload(profession="AB")  # 2 chars, under the 3-char minimum
    res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert res.status_code == 422


def test_admin_rejects_too_short_subagent_name(client):
    payload = valid_agent_payload()
    payload["sub_agents"][0]["name"] = "X"
    res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert res.status_code == 422


def test_admin_rejects_more_than_five_subagents(client):
    payload = valid_agent_payload()
    payload["sub_agents"] = [
        {"name": f"Sub-Agent {i}", "task": f"Does specialized thing number {i}"} for i in range(6)
    ]
    res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert res.status_code == 422


def test_admin_rejects_non_positive_number(client):
    payload = valid_agent_payload(number=0)
    res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert res.status_code == 422


def test_admin_create_then_update_reports_correctly(client, db_session):
    from app.models import Agent

    payload = valid_agent_payload(profession="Unique New Profession")
    create_res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert create_res.status_code == 200
    assert create_res.json()["created"] is True

    update_res = client.post("/admin/agents", json=payload, headers=admin_auth_header())
    assert update_res.status_code == 200
    assert update_res.json()["created"] is False

    # only one row exists for this slug — the second call updated, didn't duplicate
    assert db_session.query(Agent).filter_by(slug="unique-new-profession").count() == 1


def test_admin_resubmit_replaces_subagents_not_accumulates(client, db_session):
    from app.models import Agent, SubAgent

    payload = valid_agent_payload(profession="Sub Agent Replacement Test")
    client.post("/admin/agents", json=payload, headers=admin_auth_header())

    payload["sub_agents"] = [{"name": "Only Remaining Agent", "task": "The only one left after resubmit"}]
    client.post("/admin/agents", json=payload, headers=admin_auth_header())

    agent = db_session.query(Agent).filter_by(slug="sub-agent-replacement-test").first()
    subs = db_session.query(SubAgent).filter_by(agent_id=agent.id).all()
    assert [s.name for s in subs] == ["Only Remaining Agent"]


def test_catalog_sorts_most_recently_updated_first(client, db_session, seeded_agent, second_agent):
    from datetime import datetime, timedelta

    # Set explicit, unambiguously-ordered timestamps rather than relying on
    # fixture creation timing — two rows created microseconds apart in the
    # same test could tie, and the tiebreaker (Agent.number asc) would then
    # put seeded_agent first, making this test order-dependent and flaky.
    seeded_agent.updated_at = datetime(2020, 1, 1)
    second_agent.updated_at = datetime(2020, 1, 2)
    db_session.commit()

    res = client.get("/agents?limit=2")
    slugs = [item["slug"] for item in res.json()["items"]]
    assert slugs.index(second_agent.slug) < slugs.index(seeded_agent.slug)

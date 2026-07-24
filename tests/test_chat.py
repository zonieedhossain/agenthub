def test_chat_resolves_main_agent_system_prompt(client, seeded_agent, monkeypatch):
    captured = {}

    def fake_get_reply(system_prompt, history):
        captured["system_prompt"] = system_prompt
        return "fake reply"

    monkeypatch.setattr("app.routers.chat.get_reply", fake_get_reply)

    signup_res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    token = signup_res.json()["access_token"]

    res = client.post(
        "/agents/doctor-physician/chat",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert captured["system_prompt"] == "You are a doctor agent."


def test_chat_resolves_sub_agent_system_prompt(client, seeded_agent, db_session, monkeypatch):
    from app.models import SubAgent
    sub = SubAgent(
        agent_id=seeded_agent.id, slug="clinical-advisor", name="Clinical Advisor",
        task="advises on clinical matters", system_prompt="You are the Clinical Advisor sub-agent.",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    captured = {}
    def fake_get_reply(system_prompt, history):
        captured["system_prompt"] = system_prompt
        return "fake reply"
    monkeypatch.setattr("app.routers.chat.get_reply", fake_get_reply)

    signup_res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    token = signup_res.json()["access_token"]

    res = client.post(
        "/agents/doctor-physician/chat",
        json={"message": "hello", "sub_agent_id": sub.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert captured["system_prompt"] == "You are the Clinical Advisor sub-agent."
    # confirm it's NOT using the main agent's prompt
    assert captured["system_prompt"] != seeded_agent.system_prompt


def test_chat_rejects_sub_agent_from_different_agent(client, seeded_agent, second_agent, db_session):
    from app.models import SubAgent
    # sub-agent belongs to the LAWYER agent
    sub = SubAgent(
        agent_id=second_agent.id, slug="contract-reviewer", name="Contract Reviewer",
        task="reviews contracts", system_prompt="You are the Contract Reviewer.",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    signup_res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    token = signup_res.json()["access_token"]

    # try to use the Lawyer's sub-agent while chatting under the Doctor agent
    res = client.post(
        "/agents/doctor-physician/chat",
        json={"message": "hello", "sub_agent_id": sub.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
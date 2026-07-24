def test_signup_success(client, seeded_agent):
    res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_signup_duplicate_fails(client, seeded_agent):
    client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    assert res.status_code == 409


def test_login_success(client, seeded_agent):
    client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    res = client.post("/agents/doctor-physician/login", json={
        "email": "alice@test.com", "password": "secret123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password_fails(client, seeded_agent):
    client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    res = client.post("/agents/doctor-physician/login", json={
        "email": "alice@test.com", "password": "wrongpassword"
    })
    assert res.status_code == 401


def test_login_nonexistent_email_fails(client, seeded_agent):
    res = client.post("/agents/doctor-physician/login", json={
        "email": "nobody@test.com", "password": "secret123"
    })
    assert res.status_code == 401


def test_same_email_can_signup_under_two_different_agents(client, seeded_agent, second_agent):
    res1 = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    res2 = client.post("/agents/corporate-lawyer/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["access_token"] != res2.json()["access_token"]


def test_signup_rejects_short_password(client, seeded_agent):
    res = client.post("/agents/doctor-physician/signup", json={
        "email": "shortpw@test.com", "password": "abc123"  # 6 chars, under the 8-char minimum
    })
    assert res.status_code == 422


def test_login_is_rate_limited(client, seeded_agent):
    # 10/minute — send well past that so the assertion doesn't depend on
    # exactly which request number trips it.
    statuses = [
        client.post("/agents/doctor-physician/login", json={
            "email": "nobody@test.com", "password": "whatever123"
        }).status_code
        for _ in range(15)
    ]
    assert 429 in statuses


def test_token_from_one_agent_rejected_on_another(client, seeded_agent, second_agent):
    """THE critical isolation test — a token minted for Agent A must not work on Agent B."""
    signup_res = client.post("/agents/doctor-physician/signup", json={
        "email": "alice@test.com", "password": "secret123"
    })
    doctor_token = signup_res.json()["access_token"]

    # try using the Doctor token against the Lawyer's chat endpoint
    res = client.post(
        "/agents/corporate-lawyer/chat",
        json={"message": "test"},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res.status_code == 401
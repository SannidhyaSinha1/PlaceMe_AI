"""The mandatory onboarding gate: 403 on gated endpoints until profile + CV."""


async def test_incomplete_profile_is_gated(client):
    r = await client.post(
        "/auth/register", json={"email": "gated@test.co", "password": "test-password-123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Gated: applying and AI features.
    r = await client.post("/applications", json={"opportunity_id": 1}, headers=headers)
    assert r.status_code == 403
    r = await client.get("/ai/recommend", headers=headers)
    assert r.status_code == 403

    # Not gated: browsing and profile editing must keep working.
    assert (await client.get("/opportunities", headers=headers)).status_code == 200
    assert (await client.get("/profile/me", headers=headers)).status_code == 200


async def test_complete_profile_unlocks(client, student, admin):
    # Admin creates an opportunity the student can apply to.
    r = await client.post(
        "/opportunities",
        headers=admin["headers"],
        json={"company_name": "GateCo", "opportunity_type": "Internship"},
    )
    assert r.status_code == 201, r.text
    opp_id = r.json()["id"]

    r = await client.post(
        "/applications", json={"opportunity_id": opp_id}, headers=student["headers"]
    )
    assert r.status_code == 201, r.text
    assert r.json()["opportunity"]["company_name"] == "GateCo"


async def test_admin_exempt_from_gate(client, admin):
    r = await client.get("/ai/recommend", headers=admin["headers"])
    # Admin passes the gate; heuristic recommender answers without LLM keys.
    assert r.status_code == 200

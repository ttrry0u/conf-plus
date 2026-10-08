def _create_conf(client, admin_token):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Conf", "start_date": "2026-06-01T10:00:00", "end_date": "2026-06-03T18:00:00"},
    )
    return r.json()["id"]


def test_submit_abstract(client, admin_token, speaker_token):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/abstracts",
        headers={"Authorization": f"Bearer {speaker_token}"},
        json={
            "conference_id": conf_id,
            "title": "My Talk",
            "content": "Content with enough length for validation.",
            "duration_minutes": 30,
        },
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


def test_submit_abstract_participant_forbidden(client, admin_token, test_user):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/abstracts",
        headers={"Authorization": f"Bearer {test_user}"},
        json={
            "conference_id": conf_id,
            "title": "Talk",
            "content": "Content with enough length.",
            "duration_minutes": 30,
        },
    )
    assert r.status_code == 403


def test_submit_abstract_zero_duration(client, admin_token, speaker_token):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/abstracts",
        headers={"Authorization": f"Bearer {speaker_token}"},
        json={
            "conference_id": conf_id,
            "title": "Zero",
            "content": "Content with enough length.",
            "duration_minutes": 0,
        },
    )
    assert r.status_code == 422


def test_submit_abstract_too_long_duration(client, admin_token, speaker_token):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/abstracts",
        headers={"Authorization": f"Bearer {speaker_token}"},
        json={
            "conference_id": conf_id,
            "title": "Long",
            "content": "Content with enough length.",
            "duration_minutes": 601,
        },
    )
    assert r.status_code == 422


def test_approve_abstract(client, admin_token, speaker_token):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/abstracts",
        headers={"Authorization": f"Bearer {speaker_token}"},
        json={
            "conference_id": conf_id,
            "title": "Talk",
            "content": "Content with enough length.",
            "duration_minutes": 30,
        },
    )
    abstract_id = r.json()["id"]
    r = client.post(f"/api/abstracts/{abstract_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

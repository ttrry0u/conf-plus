def test_list_conferences_empty(client):
    r = client.get("/api/conferences")
    assert r.status_code == 200
    assert r.json() == []


def test_create_conference_admin(client, admin_token):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Test Conf", "start_date": "2026-06-01T10:00:00", "end_date": "2026-06-03T18:00:00"},
    )
    assert r.status_code == 201
    assert r.json()["title"] == "Test Conf"


def test_create_conference_participant_forbidden(client, test_user):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {test_user}"},
        json={"title": "Forbidden", "start_date": "2026-06-01T10:00:00", "end_date": "2026-06-03T18:00:00"},
    )
    assert r.status_code == 403


def test_create_conference_invalid_dates(client, admin_token):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Bad", "start_date": "2026-06-03T10:00:00", "end_date": "2026-06-01T18:00:00"},
    )
    assert r.status_code == 422


def test_get_conference_not_found(client):
    r = client.get("/api/conferences/99999")
    assert r.status_code == 404


def test_delete_conference(client, admin_token):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "ToDelete", "start_date": "2026-06-01T10:00:00", "end_date": "2026-06-03T18:00:00"},
    )
    conf_id = r.json()["id"]
    r = client.delete(f"/api/conferences/{conf_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 204

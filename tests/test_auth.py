def test_register_success(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "New User",
            "email": "new@example.com",
            "password": "secure123",
            "role": "participant",
            "consent_152fz": True,
        },
    )
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_register_duplicate_email(client, test_user):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Dup",
            "email": "test@example.com",
            "password": "secure123",
            "role": "participant",
            "consent_152fz": True,
        },
    )
    assert r.status_code == 400


def test_register_without_consent(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "No Consent",
            "email": "no@example.com",
            "password": "secure123",
            "role": "participant",
            "consent_152fz": False,
        },
    )
    assert r.status_code == 422


def test_register_weak_password(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Weak",
            "email": "weak@example.com",
            "password": "onlyletters",
            "role": "participant",
            "consent_152fz": True,
        },
    )
    assert r.status_code == 422


def test_login_success(client, test_user):
    r = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass123",
        },
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client, test_user):
    r = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrong",
        },
    )
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, test_user):
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {test_user}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_export_data(client, test_user):
    r = client.get("/api/auth/me/data", headers={"Authorization": f"Bearer {test_user}"})
    assert r.status_code == 200
    assert "profile" in r.json()


def test_delete_account(client, test_user):
    r = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {test_user}"})
    assert r.status_code == 204

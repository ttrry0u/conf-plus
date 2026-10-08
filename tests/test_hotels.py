def _create_conf(client, admin_token):
    r = client.post(
        "/api/conferences",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "HotelConf", "start_date": "2027-06-01T10:00:00", "end_date": "2027-06-03T18:00:00"},
    )
    return r.json()["id"]


def test_request_hotel_valid(client, admin_token, test_user):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/hotels",
        headers={"Authorization": f"Bearer {test_user}"},
        json={"conference_id": conf_id, "check_in": "2027-06-01", "check_out": "2027-06-03"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "requested"


def test_request_hotel_past_date(client, admin_token, test_user):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/hotels",
        headers={"Authorization": f"Bearer {test_user}"},
        json={"conference_id": conf_id, "check_in": "2020-01-01", "check_out": "2027-06-03"},
    )
    assert r.status_code == 422


def test_request_hotel_invalid_dates(client, admin_token, test_user):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/hotels",
        headers={"Authorization": f"Bearer {test_user}"},
        json={"conference_id": conf_id, "check_in": "2027-06-05", "check_out": "2027-06-01"},
    )
    assert r.status_code == 422


def test_confirm_hotel(client, admin_token, test_user):
    conf_id = _create_conf(client, admin_token)
    r = client.post(
        "/api/hotels",
        headers={"Authorization": f"Bearer {test_user}"},
        json={"conference_id": conf_id, "check_in": "2027-06-01", "check_out": "2027-06-03"},
    )
    booking_id = r.json()["id"]
    r = client.post(f"/api/hotels/{booking_id}/confirm", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

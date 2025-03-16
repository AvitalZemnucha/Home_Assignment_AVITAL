import requests
import pytest
from utils.constants import API_LOGIN_URL, API_PANEL_ADMIN


@pytest.mark.parametrize("payload, expected_status, expected_token, admin_access_expected_status, expected_detail", [
    ({"email": "jane.smith@example.com", "password": "Jane2"}, 200, True, 403, None), # Regular users should be forbidden from admin panel
    ({"email": "alice.johnson@example.com", "password": "Admin1"}, 200, True, 200, None), # Admin should have access to the admin panel
    ({"email": "invalid@example.com", "password": "wrongpassword"}, 401, False, None, "Invalid credentials"), # Invalid credentials
    ({"email": "jane.smith@example.com"}, 422, False, None, None),  # FastAPI validation error ,missing password
])
def test_login_and_admin_access(payload, expected_status, expected_token, admin_access_expected_status, expected_detail):
    response = requests.post(API_LOGIN_URL, json=payload)
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
    if expected_detail:
        assert expected_detail in response.json().get("detail", "")

    if expected_token:
        token = response.json().get("token")
        assert token, "Token was not returned in the response"
        headers = {"Authorization": f"Bearer {token}"}
        admin_response = requests.get(API_PANEL_ADMIN, headers=headers)
        assert admin_response.status_code == admin_access_expected_status, f"Expected {admin_access_expected_status}, got {admin_response.status_code}"
        if admin_access_expected_status == 200:
            assert "Welcome to the admin panel" in admin_response.json().get("message", "")

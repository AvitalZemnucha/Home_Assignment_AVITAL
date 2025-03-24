import base64

import pytest
import requests
from database.order_queries import get_order_by_id
from database.user_queries import get_user_by_id
from tests_api.helpers.cart_helpers import add_to_cart_and_checkout, clear_cart
from tests_api.helpers.validation_helpers import get_admin_auth_headers, validate_mongodb_state, change_order_status, \
    decode_user_token
from utils.constants import API_CART_URL, API_CHECKOUT_URL, API_ORDERS_ADMIN, API_ORDERS_STATUS_ADMIN, API_LOGIN_URL, \
    API_UPDATE_STATUS_ADMIN
from database.user_queries import users_data


def test_full_admin_operation(get_admin_token, get_user_token):
    #Customer creates an order, status = pending
    checkout_response, cart_payload = add_to_cart_and_checkout(get_user_token)
    checkout_data = checkout_response.json()
    order_id = checkout_data.get("order_id")
    assert order_id, "No order_id found after checkout"
    #Check that the new order is pending in DB
    decode_user_token(get_user_token)
    order_in_db = get_order_by_id(order_id)
    assert order_in_db["status"].lower() == "pending", f"Order is not pending, got {order_in_db['status']}"
   #Admin Login
    # payload = {
    #     "email": "alice.johnson@example.com",
    #     "password": "Admin1"
    # }
    admin_user =users_data[2]
    payload = {
        "email": admin_user["email"],
        "password":  base64.b64decode(admin_user["password"]).decode()
    }
    response_login = requests.post(API_LOGIN_URL, json=payload)
    assert response_login.status_code == 200, f"Expected 200, got {response_login.status_code}"
    data = response_login.json()
    admin_token = data['token']
    print(admin_token)

    # Admin Gets All Orders
    headers = get_admin_auth_headers(admin_token)
    response_all_orders = requests.get(API_ORDERS_ADMIN, headers=headers)
    assert response_all_orders.status_code == 200, f"Expected 200, got {response_all_orders.status_code}"
    orders_data = response_all_orders.json()
    assert len(orders_data) > 0, "No orders found"

    #Get first Order, verify that first order is 'Pending' in DB
    order_id = orders_data['orders'][0]['order_id']
    order_in_db = get_order_by_id(order_id)
    assert order_in_db["status"].lower() == "pending", f"Order doesn't start in pending, current: {order_in_db['status']}"

    #Check status change in DB and verify email content
    status_flow = ["Processing", "Shipped", "Delivered"]
    for new_status in status_flow:
        print(f"Changing status of order {order_id} to {new_status}")
        change_order_status(headers, order_id, new_status)
        updated_order = get_order_by_id(order_id)
        print(f"Order in DB after setting to {new_status}: {updated_order}")
        assert updated_order[
                   "status"].lower() == new_status.lower(), f"Status not updated in DB, expected {new_status}, got {updated_order['status']}"

    #Verify that trying to update a delivered order fails with 400
    payload = {
        "order_id": order_id,
        "new_status": "Delivered"  # Attempting to update to the same status
    }
    response_verify = requests.put(API_UPDATE_STATUS_ADMIN, json=payload, headers=headers)
    assert response_verify.status_code == 400, f"Expected 400 for updating already delivered order, got {response_verify.status_code}"

    # Get order by ID and verify final status
    order_details_response = requests.get(f"{API_ORDERS_ADMIN}/{order_id}", headers=headers)
    assert order_details_response.status_code == 200, f"Expected 200, got {order_details_response.status_code}"
    order_details = order_details_response.json()
    assert order_details["status"].lower() == "delivered", f"Final status incorrect, expected Delivered, got {order_details['status']}"





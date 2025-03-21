import pytest
import requests
from database.order_queries import get_order_by_id
from tests_api.helpers.cart_helpers import add_to_cart_and_checkout
from tests_api.helpers.validation_helpers import get_admin_auth_headers, validate_mongodb_state, change_order_status
from utils.constants import API_CART_URL, API_CHECKOUT_URL, API_ORDERS_ADMIN, API_ORDERS_STATUS_ADMIN



def test_create_order_and_check_db(get_user_token, orders_collection):
    # Add items to the cart and checkout
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    #Get the order from DB and validate it
    order_in_db = get_order_by_id(order_id)
    assert order_in_db["items"][0]["name"] == cart_payload[0]["name"]
    assert order_in_db["total_price"] > 0, f"Invalid total price in MongoDB order: {order_in_db['total_price']}"
    assert order_in_db["status"] == "Pending", f"Unexpected order status: {order_in_db['status']}"


def test_create_order_update_status_check_db(get_user_token, orders_collection, get_admin_token):
    # Add items to cart and checkout
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    # Admin updates the order status and verify
    headers = get_admin_auth_headers(get_admin_token)
    order_in_db = get_order_by_id(order_id)
    #First status change to "Processing"
    new_status = "Processing"
    change_order_status(headers, order_id, new_status)
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    assert admin_response.json()['status'] == new_status
    #Second status change to "Shipped"
    new_status = "Shipped"
    change_order_status(headers, order_id, new_status)
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    assert admin_response.json()['status'] == new_status


def test_customer_creates_order_delete_by_admin_and_check_order_in_db(get_user_token, orders_collection, get_admin_token):
    # Add items to cart and checkout
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    # Admin deletes the order and validate it is removed from DB
    headers =  get_admin_auth_headers(get_admin_token)
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_id}", headers=headers)
    assert admin_response.json()['status'] == "Pending", f"Unexpected status: {admin_response.json()['status']}"
    # Deleting the order
    admin_response = requests.delete(f"{API_ORDERS_ADMIN}/{order_id}", headers=headers)
    assert "deleted successfully" in admin_response.json()["message"], f"Failed to delete order {order_id}"

    # Validate the order is removed from DB
    order_in_db = get_order_by_id(order_id)
    assert order_in_db is None, f"Order {order_id} was not deleted."


@pytest.mark.parametrize("order_id", [200, 999])
def test_try_to_update_non_existing_order(get_user_token, orders_collection, get_admin_token, order_id):
    headers =  get_admin_auth_headers(get_admin_token)
    new_status = "Processing"
    payload = {
        "order_id": order_id,
        "new_status": new_status
    }
    status_change_response = requests.put(f"{API_ORDERS_ADMIN}/update-status", headers=headers, json=payload)
    assert status_change_response.json()['detail'] == "Order not found", f"Expected 'Order not found', but got {status_change_response.json()['detail']}"
    assert status_change_response.status_code == 404, f"Expected status code 404, but got {status_change_response.status_code}"

#Implemeted parameterized tests for different order statuses
@pytest.mark.parametrize("expected_status",[
    "pending",
    "processing",
    "shipped",
    "delivered"
])
def test_test_order_status(orders_collection, get_admin_token,expected_status):
    headers = get_admin_auth_headers(get_admin_token)
    status_response = requests.get(f"{API_ORDERS_STATUS_ADMIN}/{expected_status}", headers=headers)
    assert status_response.status_code == 200, f"Expected 200, but got {status_response.status_code}"
    data = status_response.json()
    for i in range(len(data['orders'])):
        assert data['orders'][i]['status'].lower() == expected_status.lower(), f"Expected {expected_status}, but got instead {data['orders'][i]['status']}"


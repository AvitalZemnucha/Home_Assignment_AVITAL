import jwt
import requests
import pytest

from database.order_queries import get_order_by_id
from database.user_queries import get_user_by_id, SECRET_KEY
from utils.constants import API_ORDERS_ADMIN, API_UPDATE_STATUS_ADMIN


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def get_admin_auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def decode_user_token(token):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return decoded_token["user_id"]

def verify_cart_item(cart_item, product_id, name, quantity, price=None):
    assert cart_item["product_id"] == product_id, f"Expected {product_id}, got {cart_item['product_id']}"
    assert cart_item["name"] == name, f"Expected {name}, got {cart_item['name']}"
    assert cart_item["quantity"] == quantity, f"Expected {quantity}, got {cart_item['quantity']}"
    if price is not None:
        assert cart_item["price"] == price, f"Expected {price}, got {cart_item['price']}"

def validate_mongodb_state(token, order_id=None, expect_empty_cart=True):
    user_id = decode_user_token(token)
    user_in_db = get_user_by_id(user_id)
    assert user_in_db, f"User with user_id '{user_id}' not found in MongoDB"
    if expect_empty_cart:
        assert user_in_db["cart"] == [], f"Expected empty cart but got {user_in_db['cart']}"
    else:
        assert len(user_in_db["cart"]) > 0, "Expected non-empty cart but got empty cart"
    if order_id:
        order = get_order_by_id(order_id)
        assert order, f"Order {order_id} not found in database"
        return order

def validate_checkout_response(response):
    checkout_data = response.json()
    assert checkout_data is not None, "Checkout response is empty"

    email_key = next((key for key in checkout_data.keys() if key.startswith("Email sent to")), None)
    assert email_key, f"No 'Email sent to' key found in response: {checkout_data}"

    email_content = checkout_data[email_key]
    if "Confirmation Email" in email_content:
        assert "order_id" in checkout_data, "Order ID missing in successful checkout"
        return "success", checkout_data["order_id"]
    elif "out of stock" in email_content:
        return "out_of_stock", None
    elif "card was declined" in email_content:
        return "card_declined", None
    else:
        pytest.fail(f"Unexpected email content: {email_content}")

def change_order_status(headers, order_id, new_status):
    payload = {
        "order_id": order_id,
        "new_status": new_status
    }
    status_change_response = requests.put(f"{API_UPDATE_STATUS_ADMIN}", headers=headers, json=payload)
    print(f"Updating order status with payload: {payload}")
    print(f"Response: {status_change_response.status_code}, {status_change_response.text}")
    assert status_change_response.status_code == 200, f"Status change failed for {order_id} to {new_status}"
    status_changed_data = status_change_response.json()
    assert new_status in status_changed_data["message"], f"Failed to update status to {new_status}"

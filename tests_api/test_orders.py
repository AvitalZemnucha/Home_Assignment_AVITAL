import time
import pytest
import requests
from bson import ObjectId
from utils.constants import API_LOGIN_URL, API_CART_URL, API_CHECKOUT_URL, API_ORDERS_ADMIN
from database.product_queries import products_data
from database.order_queries import get_order_by_id
import random


def add_to_cart_and_checkout(get_user_token):
    item = random.choice(products_data)
    del item['stock']
    item['quantity'] = random.randint(1, 10)
    cart_payload = [item]
    headers = {"Authorization": f"Bearer {get_user_token}"}
    # Create an order with random test data
    response = requests.put(API_CART_URL, headers=headers, json=cart_payload)
    # Validate the Response
    assert response.status_code == 200, f"Failed to add items to cart. Status code: {response.status_code}"
    # User Checks out
    response_checkout = requests.post(API_CHECKOUT_URL, headers=headers)

    while not "Confirmation" in response_checkout.text:
        print("Payment failed! Try another card")
        response_checkout = requests.post(API_CHECKOUT_URL, headers=headers)
    # Validate the response.
    assert response_checkout.status_code == 200, f"Failed to add items to cart. Status code: {response_checkout.status_code}"
    return response_checkout, cart_payload


def test_create_order_and_check_db(get_user_token, orders_collection):
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    # Fetch an order by ID
    order_in_db = get_order_by_id(order_id)
    assert order_in_db["items"][0]["name"] == cart_payload[0]["name"]

    # Check if the total price is greater than zero
    assert order_in_db["total_price"] > 0, (
        f"Invalid total price in MongoDB order. Expected a value greater than 0. "
        f"MongoDB Order Total Price: {order_in_db['total_price']}"
    )

    # Verify the order status is 'Pending'
    assert order_in_db["status"] == "Pending", (
        f"Unexpected order status in MongoDB! Expected: 'Pending', "
        f"MongoDB Order Status: {order_in_db['status']}"
    )


def test_create_order_update_status_check_db(get_user_token, orders_collection, get_admin_token):
    # Add items to cart
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    # Fetch an order by ID
    order_in_db = get_order_by_id(order_id)
    assert order_in_db["items"][0]["name"] == cart_payload[0]["name"]

    headers = {"Authorization": f"Bearer {get_admin_token}"}
    # Admin gets order by ID
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    print("Current status:", admin_response.json()['status'])

    new_status = "Processing"
    payload = {
        "order_id": order_id,
        "new_status": new_status
    }
    status_change_response = requests.put(f"{API_ORDERS_ADMIN}/update-status", headers=headers, json=payload)
    status_changed_data = status_change_response.json()
    print("Message after updated Status By Admin:", status_changed_data["message"])
    assert new_status in status_changed_data["message"]
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    print("Current status:", admin_response.json()['status'])
    new_status = "Shipped"
    payload = {
        "order_id": order_id,
        "new_status": new_status
    }
    status_change_response = requests.put(f"{API_ORDERS_ADMIN}/update-status", headers=headers, json=payload)
    status_changed_data = status_change_response.json()
    print("Message after updated Status By Admin:", status_changed_data["message"])
    assert new_status in status_changed_data["message"]


def test_create_delete_and_check_order_in_db(get_user_token, orders_collection, get_admin_token):
    # Add items to cart
    response_checkout, cart_payload = add_to_cart_and_checkout(get_user_token)
    data_order = response_checkout.json()
    order_id = data_order["order_id"]
    # Fetch an order by ID
    order_in_db = get_order_by_id(order_id)

    headers = {"Authorization": f"Bearer {get_admin_token}"}
    # Admin gets order by ID
    admin_response = requests.get(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    print("Current status:", admin_response.json()['status'])
    assert admin_response.json()['status'] == "Pending"
    # Admin Deletes Order
    admin_response = requests.delete(f"{API_ORDERS_ADMIN}/{order_in_db['order_id']}", headers=headers)
    order_in_db = get_order_by_id(order_id)
    assert order_in_db is None
    assert "deleted successfully" in admin_response.json()["message"]


def test_try_to_update_non_existing_order(get_user_token, orders_collection, get_admin_token):
    order_id = 200
    # No need to fetch from DB - non existing order
    headers = {"Authorization": f"Bearer {get_admin_token}"}
    new_status = "Processing"
    payload = {
        "order_id": order_id,
        "new_status": new_status
    }
    status_change_response = requests.put(f"{API_ORDERS_ADMIN}/update-status", headers=headers, json=payload)
    assert status_change_response.json()['detail'] == "Order not found"
    assert status_change_response.status_code == 404

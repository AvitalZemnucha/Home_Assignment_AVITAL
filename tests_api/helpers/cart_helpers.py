import random

from database.product_queries import products_data
from tests_api.helpers.validation_helpers import *
from utils.constants import API_CART_URL, API_CHECKOUT_URL, card_payload


def get_user_cart(token):
    headers = get_auth_headers(token)
    response = requests.get(API_CART_URL, headers=headers)
    assert response.status_code == 200, f"Failed to get cart: {response.status_code}"
    return response.json()


def clear_cart(token):
    headers = get_auth_headers(token)
    response = requests.delete(API_CART_URL, headers=headers)
    assert response.status_code == 200, f"Failed to clear cart: {response.status_code}"
    return response.json()


def add_items_to_cart(token, items=None):
    if items is None:
        items = [
            {"product_id": "p001", "name": "Laptop", "quantity": 1},
            {"product_id": "p002", "name": "Mouse", "quantity": 2}
        ]

    headers = get_auth_headers(token)
    response = requests.put(API_CART_URL, headers=headers, json=items)
    assert response.status_code == 200, f"Failed to add items to cart: {response.status_code}"
    return response.json()

def add_to_cart_and_checkout(token):
    # Select a random item from products_data and modify it for the cart
    item = random.choice(products_data)
    print(item)
    item.pop('stock', None) # Remove stock from the item
    item['quantity'] = random.randint(1, 10)  # Random quantity
    cart_payload = [item]
    headers = {"Authorization": f"Bearer {token}"}

    # Add item to cart
    response = requests.put(API_CART_URL, headers=headers, json=cart_payload)
    assert response.status_code == 200, f"Failed to add items to cart. Status code: {response.status_code}"

    # Checkout process
    response_checkout = requests.post(API_CHECKOUT_URL, headers=headers, json=card_payload)
    while not "Confirmation" in response_checkout.text:
        print("Payment failed! Trying another card...")
        response_checkout = requests.post(API_CHECKOUT_URL, headers=headers, json=card_payload)

    assert response_checkout.status_code == 200, f"Failed to checkout. Status code: {response_checkout.status_code}"
    return response_checkout, cart_payload
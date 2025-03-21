from tests_api.helpers.cart_helpers import *
from tests_api.helpers.validation_helpers import *
from utils.constants import API_ALL_PRODUCTS, API_PRODUCT_URL, API_CART_URL, API_CHECKOUT_URL


def test_get_all_products(get_user_token):
    headers = get_auth_headers(get_user_token)
    response = requests.get(API_ALL_PRODUCTS, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "products" in data, f"'products' key not in response: {data}"
    assert data['products'][0]['name'] == "Laptop", f"First product should be Laptop, got {data['products'][0]['name']}"


def test_get_product_by_id(get_user_token, products_collection):
    product = products_collection.find_one()
    if not product:
        pytest.skip("No product available in DB")

    product_id = product["product_id"]
    headers = get_auth_headers(get_user_token)
    response = requests.get(f"{API_PRODUCT_URL}/{product_id}", headers=headers)

    assert response.status_code == 200
    product_data = response.json()
    assert "Laptop" in product_data['product'][
        'name'], f"Product name should contain 'Laptop', got {product_data['product']['name']}"


def test_add_to_cart_and_verify(get_user_token):
    user_id = decode_user_token(get_user_token)
    headers = get_auth_headers(get_user_token)
    #Clean cart
    clear_cart(get_user_token)
    #Add items to cart
    cart_payload = [{"product_id": "p001", "name": "Laptop", "quantity": 2}]
    response = requests.put(API_CART_URL, headers=headers, json=cart_payload)

    assert response.status_code == 200
    cart_data = response.json()
    assert cart_data is not None, "API response is empty"
    assert cart_data['message'] == "Cart updated successfully"
    # Verify API response
    verify_cart_item(cart_data['cart'][0], "p001", "Laptop", 2)
    # Verify MongoDB state
    user_in_db = get_user_by_id(user_id)
    assert user_in_db is not None, f"User with user_id '{user_id}' not found in MongoDB"
    assert 'cart' in user_in_db, "Cart not found in user's MongoDB document"
    assert len(user_in_db['cart']) > 0, "Cart is empty in MongoDB"
    verify_cart_item(user_in_db['cart'][0], "p001", "Laptop", 2, 1200)
    # Verify through get cart API
    cart_response = requests.get(API_CART_URL, headers=headers)
    assert cart_response.status_code == 200
    cart_items = cart_response.json()
    verify_cart_item(cart_items['cart'][0], "p001", "Laptop", 2)


def test_update_cart_quantity(get_user_token):
    headers = get_auth_headers(get_user_token)
    clear_cart(get_user_token)
    # Add initial quantity
    initial_quantity = 1
    add_items_to_cart(get_user_token, [{"product_id": "p001", "name": "Laptop", "quantity": initial_quantity}])
    # Add more quantity
    additional_quantity = 2
    cart_payload = [{"product_id": "p001", "name": "Laptop", "quantity": additional_quantity}]
    response = requests.put(API_CART_URL, headers=headers, json=cart_payload)
    assert response.status_code == 200
    cart_data = response.json()
    # Verify expected quantity
    expected_quantity = initial_quantity + additional_quantity
    verify_cart_item(cart_data['cart'][0], "p001", "Laptop", expected_quantity)
    # Verify in MongoDB
    user_id = decode_user_token(get_user_token)
    user_in_db = get_user_by_id(user_id)
    verify_cart_item(user_in_db['cart'][0], "p001", "Laptop", expected_quantity, 1200)


def test_clear_cart(get_user_token):
    #Add items to ensure cart is not empty
    cart_data = add_items_to_cart(get_user_token)
    assert cart_data is not None, "API response is empty"
    response = clear_cart(get_user_token)
    assert response['cart'] == [], "Cart should be empty after clearing"
    #Verify in MongoDB
    user_id = decode_user_token(get_user_token)
    user_in_db = get_user_by_id(user_id)
    assert user_in_db is not None
    assert "cart" in user_in_db, "Cart field not found"
    assert len(user_in_db['cart']) == 0, f"Cart should be empty, got {len(user_in_db['cart'])} items"


def test_checkout_process(get_user_token):
    #Add items to ensure cart is not empty
    cart_data = add_items_to_cart(get_user_token)
    assert cart_data is not None, "API response is empty"
    #Checkout
    headers = get_auth_headers(get_user_token)
    checkout_response = requests.post(API_CHECKOUT_URL, headers=headers, json=card_payload)
    assert checkout_response.status_code == 200, "Checkout failed"
    #Validate checkout response
    checkout_status, order_id = validate_checkout_response(checkout_response)
    #Validate post-checkout state
    if checkout_status == "success":
        order = validate_mongodb_state(get_user_token, order_id)
        assert order, f"Order {order_id} should exist in the database"

@pytest.mark.parametrize("product_id, product_name, quantity",[
    ("p001", "Laptop", 1),
    ("p002", "Mouse", 2),
    ("p003", "Keyboard", 3)
])
def test_add_single_item_to_cart(get_user_token, product_id, product_name, quantity):
    #Ensure that cart is empty
    clear_cart(get_user_token)
    cart_payload = [{"product_id":product_id, "name":product_name, "quantity":quantity}]
    headers = get_auth_headers(get_user_token)
    response = requests.put(API_CART_URL, headers=headers, json=cart_payload)
    assert response.status_code == 200, f"Expected 200, but instead got {response.status_code}"
    cart_data = response.json()
    verify_cart_item(cart_data['cart'][0],product_id,product_name,quantity)

@pytest.mark.parametrize("items", [
    ([{"product_id": "p001", "name": "Laptop", "quantity": 1}]),
    ([{"product_id": "p002", "name": "Mouse", "quantity": 2}]),
    ([{"product_id": "p003", "name": "Keyboard", "quantity": 3}]),
    ([
        {"product_id": "p001", "name": "Laptop", "quantity": 1},
        {"product_id": "p002", "name": "Mouse", "quantity": 1}
    ])
])
def test_multiple_products_in_cart(get_user_token, items):
    #Clear the cart before adding new items
    clear_cart(get_user_token)
    #Add items to the cart
    add_items_to_cart(get_user_token, items)
    #Get the updated cart
    cart = get_user_cart(get_user_token)
    #Verify that each item in the cart matches the expected item
    for cart_item, expected_item in zip(cart['cart'], items):
        verify_cart_item(
            cart_item,
            expected_item['product_id'],
            expected_item['name'],
            expected_item['quantity']
        )

    #Clear cart and verify it's empty
    response = clear_cart(get_user_token)
    assert response['cart'] == [], "Cart should be empty after clearing"
API_BASE_URL = "http://127.0.0.1:8000"

########User##############
API_LOGIN_URL = f"{API_BASE_URL}/login"
API_PRODUCT_URL = f"{API_BASE_URL}/product"
API_ALL_PRODUCTS = f"{API_BASE_URL}/products"
API_CART_URL = f"{API_BASE_URL}/cart"
API_CHECKOUT_URL = f"{API_BASE_URL}/checkout"
API_ORDERS_URL = f"{API_BASE_URL}/orders"

########ADMIN############
API_PANEL_ADMIN = f"{API_BASE_URL}/panel"
API_ORDERS_ADMIN = f"{API_BASE_URL}/panel/orders"
API_ORDERS_STATUS_ADMIN = f"{API_BASE_URL}/panel/orders/status"
API_UPDATE_STATUS_ADMIN = f"{API_BASE_URL}/panel/orders/update-status"


#####Credit Card######
card_payload = {
    "name": "John Doe",
    "credit_card_number": "5875616386943986",
    "expiry_date": "08/29",
    "cvv": "714"
}
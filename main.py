from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
import random
from typing import Optional, List, Dict
from fastapi.responses import HTMLResponse
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Header, Depends, Query
from pycparser.ply.yacc import Production
from pydantic import BaseModel
import base64
import jwt
from pymongo import UpdateOne

from database.mongo_db_connection import clean_collections, products_collection, users_collection
from database.order_id_tracker import insert_orders_tracker, update_last_order_id, get_last_order_id
from database.user_queries import insert_users, get_user_by_email, \
    validate_token, get_user_by_id
from database.product_queries import insert_products, update_product_stock
from database.order_queries import insert_orders, create_order as db_create_order, get_orders_by_status, \
    get_order_by_id, get_all_orders, update_order_status_in_db, delete_all_orders, delete_order_by_id_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Clearing the database.")
    clean_collections()
    print("Inserting initial data...")
    insert_users()
    insert_orders_tracker()
    insert_products()
    insert_orders()
    print("All data inserted successfully!")
    yield
    # Shutdown logic
    print("Application is shutting down")


app = FastAPI(lifespan=lifespan)


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class Order(BaseModel):
    user_id: str
    items: list[OrderItem]
    total_price: float
    status: str


class LoginRequest(BaseModel):
    email: str
    password: str  # The password will be base64 encoded


class CartItem(BaseModel):
    product_id: Optional[str] = None  # Optional field
    name: Optional[str] = None  # Optional field
    quantity: Optional[int] = 1
    price: Optional[int] = 0
    # Optional field (defaults to 1)


class UpdateOrderStatusRequest(BaseModel):
    order_id: int
    new_status: str


# Define valid status transitions
VALID_ORDER_STATUSES: Dict[str, str] = {
    "Pending": "Processing",
    "Processing": "Shipped",
    "Shipped": "Delivered",
    "Delivered": None  # No further transitions allowed
}

######### Credit Card #########
class CreditCard(BaseModel):
    name: str
    credit_card_number: str
    expiry_date: str
    cvv: str

def generate_credit_card_number():
    first_digit = str(random.randint(4, 5))
    remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(15)])
    return first_digit + remaining_digits

def generate_expiry_date():
    today = datetime.now()
    # Randomly decide if the card will be expired or valid
    if random.choice([True, False]):
        # Generate expired date
        past_date = today - timedelta(days=random.randint(1, 365 * 5))  # Subtract random days
        return past_date.strftime('%m/%y')
    else:
        # Generate valid expiry date
        future_date = today + timedelta(days=random.randint(365, 5 * 365))  # Add random days
        return future_date.strftime('%m/%y')

def generate_cvv():
    return f"{random.randint(100, 999)}"

def create_generated_card(name: str) -> CreditCard:
    return CreditCard(
        name=name,
        credit_card_number=generate_credit_card_number(),
        expiry_date=generate_expiry_date(),
        cvv=generate_cvv()
    )

@app.get("/credit_card")
async def get_card(name: str = Query(..., description="Name of the card holder")):
    card = create_generated_card(name)
    return card
def get_current_timestamp():
    return datetime.now()

##### Order Placement Flow #####
@app.get("/")
async def home():
    return "Greetings! You are on Order Management System"


@app.post("/login")
async def login(credentials: LoginRequest):
    # Fetch the user from MongoDB by email
    user = get_user_by_email(credentials.email)  # Implement this function to fetch user by email
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Encode the provided password to base64
    encoded_password = base64.b64encode(credentials.password.encode("utf-8")).decode("utf-8")
    # Retrieve the stored password from the database (base64 encoded)
    stored_password = user["password"]  # Assuming the password is stored as base64 in the DB
    # Compare the encoded password with the stored password
    if encoded_password != stored_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Return the stored token if credentials are correct
    if user["role"]["is_admin"]:
        return {"message": "Weclome admin! You are redirected to OMS Admin Panel", "token": user["token"]}
    return {"token": user["token"]}


# Function to extract the token from the Authorization header
def get_token_from_header(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid token format")
    return authorization[7:]  # Remove 'Bearer ' part


def serialize_product(product: dict) -> dict:
    # Convert _id from ObjectId to string and return only the necessary fields
    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "price": product["price"]
    }


@app.get("/products")
async def get_products(token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch products if token is valid
    products_cursor = products_collection.find({}, {"_id": 0})  # Exclude _id field from the query
    products = [serialize_product(product) for product in products_cursor]

    return {"products": products}


@app.get("/product/{product_id}")
async def user_get_product_by_id(product_id: str, token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch the product by its product_id
    product = products_collection.find_one({"product_id": product_id}, {"_id": 0})

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Serialize the product before returning
    product = serialize_product(product)

    return {"product": product}


@app.get("/cart")
async def get_cart(token: str = Depends(get_token_from_header)):
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return {"cart": user_data.get("cart", [])}


from fastapi import HTTPException
from typing import List


@app.put("/cart")
async def update_cart(cart_items: List[CartItem], token: str = Depends(get_token_from_header)):
    # Check if cart_items is empty
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart items list cannot be empty")

    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get the user data from the database
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    cart = user_data.get("cart", [])

    # Iterate through each cart item for validation and updating
    for cart_item in cart_items:
        # Check if the product_id is valid and get product data
        product_data = products_collection.find_one({"product_id": cart_item.product_id})
        if not product_data:
            raise HTTPException(status_code=400, detail=f"Invalid product_id: {cart_item.product_id}")

        # Extract the price from the product data
        product_price = product_data["price"]

        # Validate product name (optional, depending on how you're handling this)
        if product_data["name"] != cart_item.name:
            raise HTTPException(status_code=400, detail=f"Product name mismatch: {cart_item.name}")

        # Validate quantity (it should be an integer and within 1 to 10)
        if not isinstance(cart_item.quantity, int):
            raise HTTPException(status_code=400,
                                detail=f"Quantity for product {cart_item.product_id}. Please provide a valid number.")
        if cart_item.quantity <= 0 or cart_item.quantity > 10:
            raise HTTPException(status_code=400,
                                detail=f"Quantity for product {cart_item.product_id} must be between 1 and 10.")

        # Update the cart with the new quantity or add the item if it doesn't exist
        updated = False
        for item in cart:
            if item["product_id"] == cart_item.product_id:
                item["quantity"] += cart_item.quantity  # Increment the quantity instead of replacing
                updated = True
                break

        # If the product is not already in the cart, append it to the cart
        if not updated:
            cart.append({
                "product_id": cart_item.product_id,
                "name": cart_item.name,
                "quantity": cart_item.quantity,
                "price": product_price  # Add the fetched price here
            })

    # Update the user's cart in the database
    users_collection.update_one({"user_id": user["user_id"]}, {"$set": {"cart": cart}})

    # Return a success message along with the updated cart
    return {"message": "Cart updated successfully", "cart": cart}


@app.delete("/cart")
async def clear_cart(token: str = Depends(get_token_from_header)):
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Empty the cart by setting it to an empty list
    users_collection.update_one({"user_id": user["user_id"]}, {"$set": {"cart": []}})

    return {"message": "All products removed from cart", "cart": []}


@app.post("/checkout")
async def checkout(credit_card: CreditCard, token: str = Depends(get_token_from_header)):
     # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Validate card expiry date
    current_date = datetime.now()
    expiry_date = datetime.strptime(credit_card.expiry_date, "%m/%y")
    if expiry_date < current_date:
        return {
            f"Email sent to {user['email']}": f"Dear {user['full_name']}, your card has expired. Please use a valid card."
        }

    # Get user's cart
    user_data = get_user_by_email(user["email"])
    if not user_data or "cart" not in user_data or not user_data["cart"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    cart_items = user_data["cart"]

    # Mock payment system
    payment_success = random.choice([True, False])
    if not payment_success:
        return {
            f"Email sent to {user['email']}": f"Dear {user['full_name']}, your card was declined. Please check with your bank if you have a balance."
        }

    # Check stock availability and calculate total price
    out_of_stock_items = []
    total_price = 0
    update_operations = []

    for item in cart_items:
        product = products_collection.find_one({"product_id": item["product_id"]})
        if not product:
            continue  # Product not found, assume it's unavailable

        if item["quantity"] > product["stock"]:
            out_of_stock_items.append(product["name"])
        else:
            total_price += product["price"] * item["quantity"]
            # Prepare the stock decrement operation
            update_operations.append(
                UpdateOne(
                    {"product_id": item["product_id"]},
                    {"$inc": {"stock": -item["quantity"]}}
                )
            )

    if out_of_stock_items:
        return {
            f"Email sent to {user['email']}": f"Dear {user['full_name']}, sorry - the following items are out of stock: {', '.join(out_of_stock_items)}. Your card will be refunded."
        }

    # Apply stock updates
    if update_operations:
        products_collection.bulk_write(update_operations)

    # Get the incremented order_id
    order_id = update_last_order_id()  # Ensure this is properly incremented

    # Create the order
    order_data = {
        "user_id": user["user_id"],
        "items": cart_items,
        "total_price": total_price,
        "status": "Pending",
        "created_at": get_current_timestamp(),
        "updated_at": get_current_timestamp(),
        "order_id": order_id,
    }

    db_create_order(order_data)

    # Clear user's cart after successful order placement
    users_collection.update_one({"user_id": user["user_id"]}, {"$set": {"cart": []}})
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$push": {"orders": {"order_id": order_id, "total_price": total_price}}}
    )

    return {
        f"Email sent to {user['email']}": f"Confirmation Email: Dear {user['full_name']}, your order is pending. Order details: {order_data['items']}, Total price: ${total_price}. We'll keep you posted on the progress.",
        "order_id": order_id  # Return the correct order_id
    }


@app.get("/orders")
async def get_orders(token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user's data
    user_data = get_user_by_email(user["email"])
    if not user_data or "orders" not in user_data or not user_data["orders"]:
        raise HTTPException(status_code=400, detail="No orders found")

    # Retrieve the orders
    orders = user_data["orders"]
    order_list = [{"order_id": order["order_id"], "total_price": order["total_price"]} for order in orders]

    return {"orders": order_list}


@app.get("/orders/{order_id}")
async def user_get_order_by_id(order_id: str, token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user data
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure "orders" exists and is a list
    if not isinstance(user_data.get("orders"), list) or not user_data["orders"]:
        raise HTTPException(status_code=400, detail="No orders found")

    # Convert order_id to int
    try:
        order_id = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Find the order
    order = next((order for order in user_data["orders"] if order.get("order_id") == order_id), None)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Return the order details
    return {
        "order_id": order["order_id"],
        "total_price": order["total_price"]
    }


####### Order Processing Flow (Admin Panel) ######
@app.get("/panel")
async def get_panel(token: str = Depends(get_token_from_header)):
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Check if the user is an admin
    if not user["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if the user is an admin

    return {"message": "Welcome to the admin panel OMS Admin Panel, please take care of the pending orders!"}


@app.get("/panel/orders")
async def list_pending_orders(token: str = Depends(get_token_from_header)):
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch pending orders
    orders = get_all_orders()
    if not orders:
        return {"orders": [], "message": "No orders found"}
    return {"orders": orders}


@app.get("/panel/orders/{order_id}")
async def admin_get_order_by_id(order_id: int, token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user's data
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Find the order by order_id
    order = get_order_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "user_id": order["user_id"],
        "status": order["status"],
        "items": order["items"],
        "total_price": order["total_price"],
        "created_at": order["created_at"].isoformat(),  # Including created_at and updated_at
        "updated_at": order["updated_at"].isoformat(),
    }


@app.delete("/panel/orders/{order_id}")
async def admin_delete_order_by_id(order_id: int, token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user's data
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get the order data
    order_data = get_order_by_id(order_id)

    if not order_data or 'error' in order_data:
        raise HTTPException(status_code=404, detail="Order not found or deleted already")

    # Check if the order status is Pending
    if order_data["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Only Pending orders can be deleted")

    # Delete the order from the database
    delete_result = delete_order_by_id_admin(order_id)

    # Check if delete operation was successful
    if not delete_result:
        raise HTTPException(status_code=404, detail="Order not found or already deleted")

    # Remove the order from the user document
    users_collection.update_one(
        {"orders.order_id": order_id},  # Find the user who has this order
        {"$pull": {"orders": {"order_id": order_id}}}  # Remove only this order
    )

    # Send refund email message
    refund_message = (
        f"Dear {get_user_by_id(order_data['user_id'])['full_name']},\n\n"
        f"Your order {order_id} has been deleted as requested.\n"
        f"The total amount of ${order_data['total_price']} will be refunded.\n\n"
        f"Thank you for shopping with us."
    )
    return {"message": f"Order {order_id} deleted successfully", "email": f"{refund_message}"}


@app.delete("/panel/orders")
async def admin_delete_all_orders(token: str = Depends(get_token_from_header)):
    # Validate the token
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user's data
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch all orders
    orders = get_all_orders()
    if not orders:
        return {"message": "No orders found to delete"}

    # Delete all orders
    delete_result = delete_all_orders()  # Function to remove all orders from the database

    # Remove orders from user documents
    users_collection.update_many({}, {"$set": {"orders": []}})

    if not delete_result:
        raise HTTPException(status_code=500, detail="Failed to delete orders")
    email = ''
    # Send refund emails
    for order in orders:
        refund_message = (
            f"Dear {get_user_by_id(order['user_id'])['full_name']},\n\n"
            f"Your order {order['order_id']} has been deleted as requested.\n"
            f"The total amount of ${order['total_price']} will be refunded.\n\n"
            f"Thank you for shopping with us."
        )
        email += send_email(get_user_by_id(order['user_id'])["email"], refund_message)

    return {"message": f"All {len(orders)} orders deleted successfully", "email": f"{email}"}


@app.get("/panel/orders/status/{status}")
async def list_orders_by_status(status: str, token: str = Depends(get_token_from_header)):
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    # Fetch orders by status
    if status.capitalize() not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=404, detail="Status not found")
    orders = get_orders_by_status(status.capitalize())
    return {"orders": orders}


@app.put("/panel/orders/update-status")
async def update_order_status(
        request: UpdateOrderStatusRequest, token: str = Depends(get_token_from_header)
):
    # Token validation (ensure this function is defined elsewhere)
    is_valid, user = validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # User validation (ensure this function is defined elsewhere)
    user_data = get_user_by_email(user["email"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure the user is an admin
    if not user_data["role"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch order by ID
    order = get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Ensure the 'status' field is present
    if "status" not in order:
        raise HTTPException(status_code=400, detail="Order status is missing")

    current_status = order["status"]
    new_status = request.new_status

    # Validate status transition
    if current_status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid current status: {current_status}")

    expected_next_status = VALID_ORDER_STATUSES[current_status]
    if expected_next_status is None:
        raise HTTPException(status_code=400, detail=f"Order is already delivered and cannot be updated.")

    if new_status != expected_next_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition: {current_status} → {new_status}. "
                   f"Valid next status is: {expected_next_status}."
        )

    # Update the order status in DB
    updated_order = update_order_status_in_db(request.order_id, new_status)
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Send email notification
    status_messages = {
        "Processing": f"Dear  {get_user_by_id(updated_order['user_id'])['full_name']}, your order #{request.order_id} is now being processed.",
        "Shipped": f"Dear  {get_user_by_id(updated_order['user_id'])['full_name']}, your order #{request.order_id} has been shipped.",
        "Delivered": f"Dear  {get_user_by_id(updated_order['user_id'])['full_name']}, your order #{request.order_id} has been delivered.",
    }
    # Update product stock if status changes to "Shipped"
    if new_status == "Shipped":
        for item in updated_order["items"]:
            product = get_product_by_id(item["product_id"])
            if product:
                new_stock = product["stock"] - item["quantity"]
                if new_stock < 0:
                    raise HTTPException(
                        status_code=400, detail=f"Not enough stock for product: {product['name']}"
                    )
                update_product_stock(item["product_id"], new_stock)
    return {
        "message": f"Order {request.order_id} status updated to {new_status} ",
        "email": f"{send_email(get_user_by_id(updated_order['user_id'])['email'], status_messages[new_status])}",
        "order": str(updated_order),
    }


def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"  # Placeholder for actual email sending logic


def get_product_by_id(product_id: str):
    product = products_collection.find_one({"product_id": product_id})
    return product


def get_product_by_name(name: str):
    product = products_collection.find_one({"name": name})
    return product


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

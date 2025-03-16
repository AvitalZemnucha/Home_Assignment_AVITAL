from typing import Optional, List
from datetime import datetime
from database.mongo_db_connection import orders_collection

orders_data = [
    {
        "user_id": "u12345",
        "items": [
            {"product_id": "p001", "name": "Laptop", "price": 1200, "quantity": 1},
            {"product_id": "p002", "name": "Mouse", "price": 25, "quantity": 2},
        ],
        "total_price": 1250,
        "status": "Pending",
        "created_at": datetime(2025, 2, 19, 12, 0),
        "updated_at": datetime(2025, 2, 19, 12, 5),
        "order_id": 4
    },
    {
        "user_id": "u23456",
        "items": [
            {"product_id": "p003", "name": "Keyboard", "price": 60, "quantity": 1},
            {"product_id": "p004", "name": "Monitor", "price": 300, "quantity": 1},
        ],
        "total_price": 360,
        "status": "Shipped",
        "created_at": datetime(2025, 2, 20, 14, 30),
        "updated_at": datetime(2025, 2, 20, 15, 0),
        "order_id": 2
    },
    {
        "user_id": "u23456",
        "items": [
            {"product_id": "p005", "name": "Headphones", "price": 150, "quantity": 1},
        ],
        "total_price": 150,
        "status": "Delivered",
        "created_at": datetime(2025, 2, 21, 9, 0),
        "updated_at": datetime(2025, 2, 21, 9, 10),
        "order_id": 1
    },
    {
        "user_id": "u23456",
        "items": [
            {"product_id": "p005", "name": "Headphones", "price": 150, "quantity": 1},
        ],
        "total_price": 150,
        "status": "Processing",
        "created_at": datetime(2025, 2, 22, 9, 0),
        "updated_at": datetime(2025, 2, 22, 9, 10),
        "order_id": 3
    },
]


def insert_orders():
    orders_collection.insert_many(orders_data)


def create_order(order_data):
    order_data['created_at'] = datetime.now()
    order_data['updated_at'] = datetime.now()
    result = orders_collection.insert_one(order_data)
    order_data['order_id'] = result.inserted_id  # Ensure order_id reflects the inserted id
    return str(result.inserted_id)


def get_orders_by_status(status: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    # Prepare the query
    query = {"status": status}

    # Optionally filter by created_at date range
    if start_date or end_date:
        date_filter = {}
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
                date_filter["$gte"] = start_date
            except ValueError:
                raise ValueError("Invalid start_date format. Expected YYYY-MM-DD.")

        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                date_filter["$lte"] = end_date
            except ValueError:
                raise ValueError("Invalid end_date format. Expected YYYY-MM-DD.")

        query["created_at"] = date_filter  # Apply both start_date and end_date if provided

    # Fetch orders from the database
    orders_cursor = orders_collection.find(query)
    orders = [
        {**order, "_id": str(order["_id"])}  # Convert ObjectId to string
        for order in orders_cursor
    ]

    return orders


def get_all_orders() -> List[dict]:
    """
    Retrieve all orders from the database.
    Converts MongoDB ObjectId to string for JSON serialization.
    """
    orders_cursor = orders_collection.find({})
    orders = [
        {**order, "_id": str(order["_id"])}  # Convert ObjectId to string
        for order in orders_cursor
    ]
    return orders


def get_order_by_id(order_id: int):
    try:
        # Ensure order_id is passed as an integer, as per the database's schema
        order = orders_collection.find_one({"order_id": order_id})
        if order:
            order["order_id"] = order_id  # Ensure the order_id is correct
        return order
    except Exception as e:
        return {"error": str(e)}


def update_order_status_in_db(order_id: int, new_status: str):
    try:
        # Update order status and timestamp
        update_result = orders_collection.update_one(
            {"order_id": order_id},  # Use integer order_id for query
            {"$set": {"status": new_status, "updated_at": datetime.now()}}
        )
        # Retrieve the updated order after the update
        updated_order = get_order_by_id(order_id)
        # Ensure the updated order has the correct status
        return updated_order
    except Exception as e:
        return {"error": str(e)}


def delete_order_by_id_admin(order_id: int):
    try:
        # Try to delete the order using the integer order_id
        delete_result = orders_collection.delete_one({"order_id": order_id})

        if delete_result.deleted_count == 0:
            return {"error": "Order not found or already deleted"}

        return {"message": f"Order {order_id} deleted successfully."}
    except Exception as e:
        return {"error": str(e)}


def delete_all_orders():
    result = orders_collection.delete_many({})  # Deletes all documents in the collection
    return result.deleted_count > 0

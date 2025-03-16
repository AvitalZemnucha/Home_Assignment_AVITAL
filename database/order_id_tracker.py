from typing import Optional

from database.mongo_db_connection import orders_tracker_collection

# Initial order tracker data
order_tracker_data = {"last_order": 4}


def insert_orders_tracker():
    if not orders_tracker_collection.find_one({}):  # Avoid duplicate insertions
        orders_tracker_collection.insert_one(order_tracker_data)
        print("Inserted initial order tracker.")


def get_last_order_id() -> Optional[int]:
    last_order = orders_tracker_collection.find_one({}, {"last_order": 1})
    return last_order["last_order"] if last_order else None


def update_last_order_id() -> int:
    result = orders_tracker_collection.update_one({}, {"$inc": {"last_order": 1}})

    if result.matched_count == 0:  # If no document exists, create one
        insert_orders_tracker()
        # Increment the last_order immediately after inserting
        result = orders_tracker_collection.update_one({}, {"$inc": {"last_order": 1}})
    # Retrieve and return the updated order ID immediately after the increment
    return get_last_order_id()  # Retrieve and return the new order ID

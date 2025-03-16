from database.mongo_db_connection import products_collection

products_data = [
    {"product_id": "p001", "name": "Laptop", "price": 1200, "stock": 100},
    {"product_id": "p002", "name": "Mouse", "price": 25, "stock": 150},
    {"product_id": "p003", "name": "Keyboard", "price": 60, "stock": 200},
    {"product_id": "p004", "name": "Monitor", "price": 300, "stock": 80},
    {"product_id": "p005", "name": "Headphones", "price": 150, "stock": 120},
    {"product_id": "p006", "name": "Mousepad", "price": 15, "stock": 120},
    {"product_id": "p007", "name": "Disc", "price": 15, "stock": 1},
]


def insert_products():
    products_collection.insert_many(products_data)


def update_product_stock(product_id, new_stock):
    # Update the stock of the product with the given product_id
    result = products_collection.update_one(
        {"product_id": product_id},  # Find the product by product_id
        {"$set": {"stock": new_stock}}  # Set the new stock value
    )

    # Check if a document was updated
    if result.modified_count > 0:
        return f"Stock for product {product_id} updated successfully."
    else:
        return f"Product {product_id} not found or stock is already the same."

from pymongo import MongoClient

# Default connection string (do not use production)
MONGO_URI = "mongodb://localhost:27017/"

# Initialize MongoDB connection
client = MongoClient(MONGO_URI)
db = client["oms_db"]

# Collection references
users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]
orders_tracker_collection = db["orders_tracker"]


def clean_collections():
    collections = db.list_collection_names()
    for collection in collections:
        db.drop_collection(collection)
        print(f"Collection {collection} has been removed.")

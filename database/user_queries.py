from database.mongo_db_connection import users_collection
import base64
import jwt
import datetime

SECRET_KEY = "my_super_secret_key"


def generate_token(user_id, email, role):
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        # "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1), for simplicity tokens will be constant
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")  # Corrected encoding method


# Passwords should be hashed using a proper hashing algorithm and salt, not base64 encoded
# Tokens should have expiration, signed and not be saved on server
users_data = [
    {"user_id": "u12345", "full_name": "John Doe", "email": "john.doe@example.com", "role": {"is_admin": False},
     "password": base64.b64encode("John1".encode()).decode(),  # Replace this with hashed password in real life
     "token": generate_token("u12345", "john.doe@example.com", {"is_admin": False}),
     "cart": [{"product_id": "p001", "name": "Laptop", "price": 1200, "quantity": 1},
              {"product_id": "p002", "name": "Mouse", "price": 25, "quantity": 2}],
     "orders": [{"order_id": 4, "total_price": 1250}]},
    {"user_id": "u23456", "full_name": "Jane Smith", "email": "jane.smith@example.com", "role": {"is_admin": False},
     "password": base64.b64encode("Jane2".encode()).decode(),  # Replace this with hashed password in real life
     "token": generate_token("u23456", "jane.smith@example.com", {"is_admin": False}), "cart": [],
     "orders": [{"order_id": 1, "total_price": 150}, {"order_id": 2, "total_price": 360},
                {"order_id": 3, "total_price": 150}]},
    {"user_id": "u34567", "full_name": "Alice Johnson", "email": "alice.johnson@example.com",
     "role": {"is_admin": True},
     "password": base64.b64encode("Admin1".encode()).decode(),  # Replace this with hashed password in real life
     "token": generate_token("u34567", "alice.johnson@example.com", {"is_admin": True}), "cart": [], "orders": []}
]


def insert_users():
    users_collection.insert_many(users_data)


def get_users(is_admin=None):
    query = {}
    if is_admin is not None:
        query["role.is_admin"] = is_admin
    return list(users_collection.find(query))


def get_user_by_email(email: str):
    user = users_collection.find_one({"email": email})
    return user


def get_user_by_id(user_id: str):
    user = users_collection.find_one({"user_id": user_id})
    return user


def validate_token(token: str):
    try:
        # Decode the token
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_payload.get("user_id")
        if not user_id:
            return False, None  # Invalid token, missing user_id
        # Fetch the user from MongoDB
        user = users_collection.find_one({"user_id": user_id}, {"_id": 0})
        if user and user.get("token") == token:
            return True, user  # Token is valid, return user data
        return False, None  # User not found or token mismatch

    except jwt.ExpiredSignatureError:
        return False, None  # Token has expired
    except jwt.InvalidTokenError:
        return False, None  # Token is invalid

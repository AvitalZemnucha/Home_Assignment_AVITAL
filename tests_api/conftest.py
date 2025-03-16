import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
import base64
from pymongo import MongoClient
import pytest
import requests
from utils.constants import API_LOGIN_URL, API_CART_URL, API_CHECKOUT_URL, API_ORDERS_URL
from database.user_queries import users_data


@pytest.fixture(scope="session")
def get_user_token():
    email = users_data[1]["email"]
    password = (base64.b64decode(users_data[1]["password"])).decode()
    payload = {"email": email, "password": password}
    response = requests.post(API_LOGIN_URL, json=payload)
    assert response.status_code == 200, "Login failed!"
    return response.json().get("token")


@pytest.fixture(scope="session")
def get_admin_token():
    email = users_data[2]["email"]
    password = (base64.b64decode(users_data[2]["password"])).decode()
    payload = {"email": email, "password": password}
    response = requests.post(API_LOGIN_URL, json=payload)
    assert response.status_code == 200, "Login failed!"
    return response.json().get("token")


############ DB CONNECTION ###################
# Fixture to connect to MongoDB
MONGO_URI = "mongodb://localhost:27017/"

# Initialize MongoDB client and DB
client = MongoClient(MONGO_URI)
db = client["oms_db"]

# Collection references
users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]

# Fixture to connect to MongoDB
@pytest.fixture(scope="session")
def mongo_client():
    client = MongoClient(MONGO_URI)
    yield client
    client.close()

# Fixture for the 'oms_db' database
@pytest.fixture(scope="session")
def test_db(mongo_client):
    db = mongo_client["oms_db"]
    yield db # No need to clean collections after tests are done

# Fixture for the 'users' collection
@pytest.fixture(scope="session")
def users_collection(test_db):
    return test_db["users"]


# Fixture for the 'products' collection
@pytest.fixture(scope="session")
def products_collection(test_db):
    return test_db["products"]


# Fixture for the 'orders' collection
@pytest.fixture(scope="session")
def orders_collection(test_db):
    return test_db["orders"]

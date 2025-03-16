## Hi, welcome to Avtal's solution for OMS assignment

### Pre requisites

- MongoDb local instalation on default port (mongodb://localhost:27017/)
- Postman
- Python/Pytest
- python requirements installed
- Pycharm

### Assumptions

- Logged user cannot cancel order after checkout (non refundable)
- Registered users are not aware of stock amount
- 2 types of users: Admin and registered user, with role based separation
- registered user cannot access OMS Admin Panel
- admin can operate on OMS Admin Panel only (cannot purchase items)
- Admin can delete only Pending order (money back guaranteed)
- User cannot remove from cart - need to empty the cart and add items again
- MongoDb runs on localhost, without password
- Passwords should be hashed using a proper hashing algorithm and salt, not base64 encoded
- Tokens should have expiration, signed and not be saved on server, for simplicity tokens will be constant
- The currency is in USD, but prices are not necessary correct

### Pre generated Data

* Orders and users

| User ID | Full Name     | Email                     | Is Admin | Password | Order ID | Items                              | Total Price | Status     | Created At       | Updated At       | Cart Items                      |
|---------|---------------|---------------------------|----------|----------|----------|------------------------------------|-------------|------------|------------------|------------------|---------------------------------|
| u12345  | John Doe      | john.doe@example.com      | False    | John1    | 4        | Laptop (1, 1200), Mouse (2, 25)    | 1250        | Pending    | 2025-02-19 12:00 | 2025-02-19 12:05 | Laptop (1, 1200), Mouse (2, 25) |
| u23456  | Jane Smith    | jane.smith@example.com    | False    | Jane2    | 1        | Headphones (1, 150)                | 150         | Delivered  | 2025-02-21 09:00 | 2025-02-21 09:10 | None                            |
| u23456  | Jane Smith    | jane.smith@example.com    | False    | Jane2    | 2        | Keyboard (1, 60), Monitor (1, 300) | 360         | Shipped    | 2025-02-20 14:30 | 2025-02-20 15:00 | None                            |
| u23456  | Jane Smith    | jane.smith@example.com    | False    | Jane2    | 3        | Headphones (1, 150)                | 150         | Processing | 2025-02-22 09:00 | 2025-02-22 09:10 | None                            |
| u34567  | Alice Johnson | alice.johnson@example.com | True     | Admin1   | None     | None                               | None        | None       | None             | None             | None                            |

* Note that users have prepopulated orders and even items in the cart


### Instructions
To start the Backend run from project's root directory:

```bash
uvicorn main:app --reload
```
To run tests and create html report:
```bash
pytest
```


### Files attached in OMS_Files directory

- Postman collection (Avital's OMS.postman_collection.json)
- Test plan (Avital's Test Plan for Order Management System (OMS).docx)
- Test cases (Avital's Test Cases - UI Manual Testing.xlsx)











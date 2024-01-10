import sqlite3
import random
import bcrypt
from datetime import datetime
import time

# Function to generate a random name for the item
def generate_item_name():
    adjectives = ["Vintage", "Modern", "Classic", "Elegant", "Stylish", "Cozy", "Charming", "Luxurious"]
    nouns = ["Sofa", "Laptop", "Table", "Bookshelf", "Bicycle", "Camera", "Watch", "Headphones"]
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

# Function to generate a random price for the item
def generate_item_price():
    return round(random.uniform(10, 500), 2)

# Connect to the database
conn = sqlite3.connect('tellsell.db')
cursor = conn.cursor()

# Create three users
for i in range(3):
    name = f"User{i+1}"

    # Append a timestamp to ensure unique email addresses
    timestamp = int(time.time())
    email = f"{name.lower()}.{timestamp}@stud.gyminterlaken.ch"

    print(f"Creating user: {name}, Email: {email}")

    password = "password123"

    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    # Insert the user into the 'users' table
    cursor.execute("INSERT INTO users (name, password, email) VALUES (?, ?, ?)",
                   (name, hashed_password, email))

    # Get the user_id for the newly created user
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user_id = cursor.fetchone()[0]

    print(f"User created with ID: {user_id}")

    # Insert placeholder items for the user
    for _ in range(5):  # Insert 5 items for each user
        item_name = generate_item_name()
        item_desc = f"Description for {item_name}"
        item_price = generate_item_price()
        item_cat = "Category"

        # Insert the item into the 'items' table with the current timestamp
        cursor.execute("INSERT INTO items (itemname, itemdesc, price, user_id, date_added, cat) VALUES (?, ?, ?, ?, ?, ?)",
                       (item_name, item_desc, item_price, user_id, datetime.now(), item_cat))

    print(f"Items created for user with ID: {user_id}")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database populated with users and placeholder items, :D")

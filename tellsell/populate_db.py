import sqlite3
import random
import bcrypt
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
    first_name = f"User{i+1}"
    last_name = "Doe"
    
    # Append a timestamp to ensure unique email addresses
    timestamp = int(time.time())
    email = f"{first_name.lower()}.{last_name.lower()}.{timestamp}@stud.gyminterlaken.ch"
    
    print(f"Creating user: {first_name} {last_name}, Email: {email}")

    password = "password123"  # You may want to hash this password in a real scenario

    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    # Insert the user into the 'users' table
    cursor.execute("INSERT INTO users (firstname, lastname, password, email) VALUES (?, ?, ?, ?)",
                   (first_name, last_name, hashed_password, email))

    # Get the user_id for the newly created user
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user_id = cursor.fetchone()[0]

    print(f"User created with ID: {user_id}")

    # Insert placeholder items for the user
    for _ in range(5):  # Insert 5 items for each user
        item_name = generate_item_name()
        item_desc = f"Description for {item_name}"
        item_price = generate_item_price()

        cursor.execute("INSERT INTO items (itemname, itemdesc, price, user_id) VALUES (?, ?, ?, ?)",
                       (item_name, item_desc, item_price, user_id))

    print(f"Items created for user with ID: {user_id}")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database populated with three users and placeholder items.")

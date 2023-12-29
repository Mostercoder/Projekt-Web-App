from flask import Flask, url_for, render_template, redirect, session, request, g, jsonify
import sqlite3
import time
import datetime
import hashlib
import os
import bcrypt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mysecretkey')


conn = sqlite3.connect('tellsell.db')
c = conn.cursor()

DATABASE = 'tellsell.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def extract_name(email):
    # Check if the email is in the correct format
    if email.endswith("@stud.gyminterlaken.ch"):
        # Split the email address at the '@' symbol
        local_part, domain = email.split('@')

        # Split the local part at the '.' symbol
        first_name, last_name = local_part.split('.')

        return first_name, last_name
    else:
        return render_template('register')

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             firstname TEXT NOT NULL,
             lastname TEXT NOT NULL,
             password TEXT NOT NULL,
             email TEXT NOT NULL UNIQUE
             );''')

c.execute('''CREATE TABLE IF NOT EXISTS items
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             itemname TEXT NOT NULL ,
             itemdesc TEXT NOT NULL,
             price Decimal,
             user_id int
             );''')
conn.commit()
conn.close()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Retrieve form values
        password = request.form["password"]
        email = request.form["email"]

        # Generate a salt
        salt = bcrypt.gensalt()

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        # Extract first name and last name from email
        names = extract_name(email)
        
        if names:
            first_name, last_name = names

            # connect to tellsell
            conn = sqlite3.connect('tellsell.db')
            c = conn.cursor()

            try:
                # Insert the user into the database
                c.execute("INSERT INTO users (firstname, lastname, password, email) VALUES (?, ?, ?, ?)",
                          (first_name, last_name, hashed_password, email))
                conn.commit()
                print('User registered successfully')

            except Exception as e:
                print('Error registering user:', e)
                conn.rollback()
                return redirect(url_for('login'))

            finally:
                conn.close()
                return redirect(url_for('login'))
        else:
            print("Invalid email format")
            return redirect(url_for('register'))
    else:
        return render_template('register.html')



# Dictionary to keep track of login attempts and their timestamps
login_attempts = {}

# Log in a user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if there have been multiple failed login attempts within a certain time window
        if email in login_attempts:
            last_attempt_time = login_attempts[email]
            cooldown_duration = 10  # Cool-down duration in seconds
            elapsed_time = time.time() - last_attempt_time

            if elapsed_time < cooldown_duration:
                cooldown_remaining = cooldown_duration - elapsed_time
                error_message = f"Too many login attempts. Please wait {cooldown_remaining:.0f} seconds."
                return render_template('login.html', error=error_message)

        # Hash the password to compare it with the stored hash
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        conn = sqlite3.connect('tellsell.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, hashed_password))
        user = c.fetchone()
        conn.close()

        if user is not None:
            session['email'] = user[4]
            login_attempts.pop(email, None)  # Clear the login attempts for the user
            return redirect(url_for('index'))
        else:
            if email in login_attempts:
                login_attempts[email] = time.time()  # Update the timestamp for the failed attempt
            else:
                login_attempts[email] = time.time()  # Add a new entry for the failed attempt
            return render_template('login.html', error='Invalid email or password')

    else:
        return render_template('login.html')

# Index page, accessible only to logged-in users
@app.route('/')
def index():
    #if 'email' not in session:
    #    return redirect(url_for('login')) # DEVELOPMENT PURPOSES
    
    current_user_email = session.get('email', None)

    # Fetch all items from the 'items' table
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()

    print(items)  # Add this line for debugging

    return render_template('index.html', items=items, current_user_email=current_user_email)


# Log out the current user
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

#goto register page from login page
@app.route('/no_account', methods=['GET', 'POST'])
def no_account():
    return redirect(url_for('register'))

#goto login page from register page
@app.route('/much_account', methods=['GET', 'POST'])
def much_account():
    return redirect(url_for('login', _method='GET'))

#add the item into the db
@app.route('/add_item', methods=['POST', 'GET'])
def add_item():
    print("trying to get the data")
    # Get data from the request
    itemname = request.form.get('itemname')
    itemdesc = request.form.get('itemdesc')
    price = request.form.get('price')

    # Insert the item into the 'items' table
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the user_id based on the current session
    if 'email' in session:
        email = session['email']
        print(email)
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result is not None:
            user_id = result[0]

            cursor.execute('''INSERT INTO items (itemname, itemdesc, price, user_id)
                             VALUES (?, ?, ?, ?)''', (itemname, itemdesc, price, user_id))

            # Commit the changes and close the connection
            conn.commit()
            conn.close()

            return redirect(url_for('index'))
        else:
            return "User not found", 404
    else:
        return "User not logged in", 401



# Route to sell an item
@app.route('/sell_item', methods=['GET','POST'])
def sell_item():
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the list of sellers directly from the database
    cursor.execute('SELECT id, email FROM users')
    sellers = cursor.fetchall()

    return render_template('sell_item.html', sellers=sellers)

# Display all items created by the logged-in user
@app.route('/my_items', methods=['GET'])
def my_items():
    if 'email' not in session:
        return redirect(url_for('login'))

    current_user_email = session.get('email', None)

    # Fetch items created by the current user from the 'items' table
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the user_id based on the current session
    cursor.execute("SELECT id FROM users WHERE email = ?", (current_user_email,))
    result = cursor.fetchone()

    if result is not None:
        user_id = result[0]

        # Fetch items created by the user
        cursor.execute('SELECT * FROM items WHERE user_id = ?', (user_id,))
        items = cursor.fetchall()

        conn.close()

        return render_template('my_items.html', items=items, current_user_email=current_user_email)
    else:
        return "User not found", 404


# Delete a specific item created by the user
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    # Fetch the user_id based on the current session
    current_user_email = session['email']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (current_user_email,))
    result = cursor.fetchone()

    if result is not None:
        user_id = result[0]

        # Delete the item only if it belongs to the logged-in user
        cursor.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
        conn.close()

        return redirect(url_for('my_items'))
    else:
        return "User not found", 404

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, url_for, render_template, redirect, session, request, g, jsonify
import sqlite3
import time
import datetime
import hashlib
import os

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

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT NOT NULL UNIQUE,
             password TEXT NOT NULL);''')

c.execute('''CREATE TABLE IF NOT EXISTS items
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             itemname TEXT NOT NULL ,
             itemdesc TEXT NOT NULL,
             price Decimal,
             user_id int);''')
conn.commit()
conn.close()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Retrieve form values
        username = request.form["username"]
        password = request.form["password"]

        # Hash the password
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()

        # connect to tellsell
        conn = sqlite3.connect('tellsell.db')
        c = conn.cursor()

        try:
            # Insert the user into the database
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
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
        return render_template('register.html')



# Dictionary to keep track of login attempts and their timestamps
login_attempts = {}

# Log in a user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if there have been multiple failed login attempts within a certain time window
        if username in login_attempts:
            last_attempt_time = login_attempts[username]
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
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = c.fetchone()
        conn.close()

        if user is not None:
            session['username'] = user[1]
            login_attempts.pop(username, None)  # Clear the login attempts for the user
            return redirect(url_for('index'))
        else:
            if username in login_attempts:
                login_attempts[username] = time.time()  # Update the timestamp for the failed attempt
            else:
                login_attempts[username] = time.time()  # Add a new entry for the failed attempt
            return render_template('login.html', error='Invalid username or password')

    else:
        return render_template('login.html')

# Index page, accessible only to logged-in users
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch all items from the 'items' table
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()

    print(items)  # Add this line for debugging

    return render_template('index.html', items=items)


# Log out the current user
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

#goto register page from login page
@app.route('/no_account', methods=['GET', 'POST'])
def no_account():
    return redirect(url_for('register'))

#goto login page from register page
@app.route('/much_account', methods=['GET', 'POST'])
def much_account():
    return redirect(url_for('login', _method='GET'))

# Route to add an item
@app.route('/add_item', methods=['POST'])
def add_item():
    # Get data from the request
    data = request.get_json()

    # Extract item details from the data
    itemname = data.get('itemname')
    itemdesc = data.get('itemdesc')
    price = data.get('price')

    # Insert the item into the 'items' table
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the user_id based on the current session
    if 'username' in session:
        username = session['username']
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO items (itemname, itemdesc, price, user_id)
                         VALUES (?, ?, ?, ?)''', (itemname, itemdesc, price, user_id))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        return jsonify({'message': 'Item added successfully'}), 201
        return redirect(url_for('index'))
    else:
        return jsonify({'error': 'User not logged in'}), 401

# Route to sell an item
@app.route('/sell_item', methods=['GET'])
def sell_item():
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the list of sellers directly from the database
    cursor.execute('SELECT id, username FROM users')
    sellers = cursor.fetchall()

    return render_template('sell_item.html', sellers=sellers)

if __name__ == '__main__':
    app.run(debug=True)
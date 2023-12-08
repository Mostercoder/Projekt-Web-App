from flask import Flask, url_for, render_template, redirect, session, request
import sqlite3
import time
import datetime
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mysecretkey')


conn = sqlite3.connect('tellsell.db')
c = conn.cursor()

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

    username = session['username']
    return render_template('index.html')

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



if __name__ == '__main__':
    app.run(debug=True)
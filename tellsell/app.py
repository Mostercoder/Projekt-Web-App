from flask import Flask, url_for, render_template, redirect, session, request, g, jsonify, send_from_directory, flash
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
import sqlite3
import time
import hashlib
import os
import bcrypt 


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mysecretkey')

conn = sqlite3.connect('tellsell.db')
c = conn.cursor()
salt = bcrypt.gensalt()

DATABASE = 'tellsell.db'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
uploads_directory = os.path.join(os.path.dirname(__file__), '..', 'uploads')

# Check if the 'uploads' folder exists, create it if not
if not os.path.exists(uploads_directory):
    os.makedirs(uploads_directory)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def is_valid_email(email):
    try:
        # Validate email
        v = validate_email(email)
        return True
    except EmailNotValidError as e:
        # Email is not valid
        return False


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT,
             password TEXT NOT NULL,
             email TEXT NOT NULL UNIQUE,
             reputation DECIMAL DEFAULT 0,
             num_reviews DECIMAL DEFAULT 0,
             is_admin INTEGER DEFAULT 0
             );''')

c.execute('''CREATE TABLE IF NOT EXISTS reviews
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             reviewer INTEGER,
             receiver INTEGER,
             rating INTEGER,
             comment TEXT,
             FOREIGN KEY (reviewer) REFERENCES users (id),
             FOREIGN KEY (receiver) REFERENCES users (id)
             );''')

c.execute('''CREATE TABLE IF NOT EXISTS items
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             itemname TEXT NOT NULL ,
             itemdesc TEXT NOT NULL,
             price Decimal,
             user_id int,
             item_picture TEXT,
             cat TEXT NOT NULL,
             date_added DATETIME
             );''')

c.execute('''CREATE TABLE IF NOT EXISTS reports
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             reporter_id INTEGER,
             reported_user_id INTEGER,
             FOREIGN KEY (reporter_id) REFERENCES users (id),
             FOREIGN KEY (reported_user_id) REFERENCES users (id)
             );''')
conn.commit()
conn.close()

def calculate_average_rating(reviews):
    if not reviews:
        return 0  # Default value when no reviews are available

    print(reviews)
    total_rating = sum(review[4] for review in reviews)  # Sum the rating from each review
    average_rating = total_rating / len(reviews)
    return round(average_rating, 2)  # Round to two decimal places for clarity


# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(os.path.join(os.path.pardir, 'uploads'), filename)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        print(request.form)
        # Retrieve form values
        password = request.form["password"]
        email = request.form["email"]
        name = request.form["name"]

        is_admin = 1 if request.form.get("password") == "admin_code" else 0

        # Validate email
        if not is_valid_email(email):
            print("Invalid email format")
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        
        # connect to tellsell
        conn = sqlite3.connect('tellsell.db')
        c = conn.cursor()
        try:
            # Insert the user into the database
            c.execute("INSERT INTO users (name, password, email, reputation, is_admin) VALUES (?, ?, ?, ?, ?)",
                (name, hashed_password, email, 0, is_admin,))
            conn.commit()
            print('User registered successfully')
        except Exception as e:
            print('Error registering user:', e)
            conn.rollback()
            return redirect(url_for('register'))
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
        email = request.form['email']
        password = request.form['password']

        # Check if there have been multiple failed login attempts within a certain time window
        if email in login_attempts:
            last_attempt_time = login_attempts[email]
            cooldown_duration = 5  # Cool-down duration in seconds
            elapsed_time = time.time() - last_attempt_time

            if elapsed_time < cooldown_duration:
                cooldown_remaining = cooldown_duration - elapsed_time
                error_message = f"Too many login attempts. Please wait {cooldown_remaining:.0f} seconds."
                return render_template('login.html', error=error_message)

        # Hash the password to compare it with the stored hash
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        print(hashed_password)
        conn = sqlite3.connect('tellsell.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, hashed_password))
        user = c.fetchone()
        print(user)
        conn.close()

        if user is not None:
            session['email'] = user[3]
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

# Index page
@app.route('/')
def index():
    #if 'email' not in session:
    #    return redirect(url_for('login')) # DEVELOPMENT PURPOSES
    
    current_user_email = session.get('email', None)

    category = request.args.get('category')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort', 'itemname')
    
    conn = sqlite3.connect('tellsell.db')
    cursor = conn.cursor()

    if search_query:
        cursor.execute('SELECT * FROM items WHERE itemname LIKE ? OR itemdesc LIKE ?',
                       (f'%{search_query}%', f'%{search_query}%'))
    elif category:
        cursor.execute('SELECT * FROM items WHERE cat = ?', (category,))
    else:
        cursor.execute(f'SELECT * FROM items ORDER BY {sort_by}')

    items = cursor.fetchall()
    conn.close()

    print(items)

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

@app.route('/add_item', methods=['POST', 'GET'])
def add_item():
    print("trying to get the data")
    
    # Get data from the request
    itemname = request.form.get('itemname')
    itemdesc = request.form.get('itemdesc')
    price = request.form.get('price')
    category = request.form.get('category')
    
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

            # Handle file upload
            if 'item_picture' in request.files:
                file = request.files['item_picture']

                if file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    relative_path = filename
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    print(file_path)

            try:
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                try:
                    cursor.execute("INSERT INTO items (itemname, itemdesc, price, user_id, item_picture, cat, date_added) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (itemname, itemdesc, price, user_id, filename, category, current_date))
                except:
                    cursor.execute("INSERT INTO items (itemname, itemdesc, price, user_id, cat, date_added) VALUES (?, ?, ?, ?, ?, ?)",
                                   (itemname, itemdesc, price, user_id, category, current_date))

                conn.commit()
            
            except Exception as e:
                print(f"Error inserting item: {e}")
                conn.rollback()

            finally:    
                conn.close()

            return redirect(url_for('index'))

        else:
            return "User not found", 404

    else:
        print("User not logged in")
        return redirect(url_for('login'))


@app.route('/process_category', methods=['POST'])
def process_category():
    selected_category = request.form.get('category')
    return f'Selected category: {selected_category}'



# Route to sell an item
@app.route('/sell_item', methods=['GET','POST'])
def sell_item():
    if 'email' not in session:
        return redirect(url_for('login'))

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

    current_user_email = session.get('email', None)

    # Fetch the user_id based on the current session
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (current_user_email,))
    user_id = cursor.fetchone()

    if user_id:
        user_id = user_id[0]

        # Retrieve the file path of the picture associated with the item
        cursor.execute("SELECT item_picture FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        picture_path = cursor.fetchone()

        if picture_path:
            picture_path = picture_path[0]
            print(picture_path)

            #check if picturepath is not empty
            if picture_path != None:
                picture_path = os.path.join(uploads_directory, picture_path)
                print(picture_path)
            
                # Delete the picture file if it exists
                if os.path.exists(picture_path):
                    os.remove(picture_path)

        # Delete the item only if it belongs to the logged-in user
        cursor.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
        conn.close()

        return redirect(url_for('my_items'))

    else:
        return "User not found", 404

@app.route('/add_review_page/<int:receiver_id>', methods=['GET'])
def add_review_page(receiver_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    return render_template('reviews.html', receiver_id=receiver_id)


@app.route('/add_review/<int:receiver_id>', methods=['POST', 'GET'])
def add_review(receiver_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    # Fetch the reviewer's user_id based on the current session
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (session['email'],))
    reviewer_id = cursor.fetchone()[0]

    if request.method == 'POST':
        # Get review data from the request
        rating = float(request.form.get('rating'))  # Convert rating to float
        comment = request.form.get('comment')

        # Check if the review already exists
        cursor.execute("SELECT id FROM reviews WHERE reviewer = ? AND receiver = ?", (reviewer_id, receiver_id))
        existing_review = cursor.fetchone()

        if existing_review:
            return redirect(url_for('index'))
        elif receiver_id != reviewer_id:
            # Insert the review into the 'reviews' table
            cursor.execute("INSERT INTO reviews (reviewer, receiver, rating, comment) VALUES (?, ?, ?, ?)",
                           (reviewer_id, receiver_id, rating, comment))

            # Update the average rating and number of reviews for the receiver
            cursor.execute("UPDATE users SET reputation = (reputation * num_reviews + ?) / (num_reviews + 1), "
                           "num_reviews = num_reviews + 1 WHERE id = ?", (rating, receiver_id))

            conn.commit()
            conn.close()

            return redirect(url_for('user_profile', user_id=receiver_id))

        else:
            conn.close()
            return redirect(url_for('index'))


    return render_template('review.html', receiver_id=receiver_id)




@app.route('/user_profile/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch user information
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        # Fetch user reviews
        cursor.execute("SELECT users.name, reviews.* FROM reviews JOIN users ON reviews.reviewer = users.id WHERE receiver = ?", (user_id,))
        user_reviews = cursor.fetchall()

        # Calculate average rating and number of reviews
        average_rating = calculate_average_rating(user_reviews)
        num_reviews = len(user_reviews)

        conn.close()

        # Pass the user_id parameter to the template
        return render_template('user_profile.html', user=user, user_reviews=user_reviews,
                       average_rating=average_rating, num_reviews=num_reviews, user_id=user_id, )
    else:
        conn.close()
        return "User not found", 404

@app.route('/report_user/<int:user_id>', methods=['POST'])
def report_user(user_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    # Fetch the reporter's user_id based on the current session
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (session['email'],))
    reporter_id = cursor.fetchone()[0]

    print(f"Reporter ID: {reporter_id}, Reported User ID: {user_id}")

    # Check if the report already exists
    cursor.execute("SELECT id FROM reports WHERE reporter_id = ? AND reported_user_id = ?", (reporter_id, user_id))
    existing_report = cursor.fetchone()

    if not existing_report and user_id != reporter_id:
        # Insert the report into the 'reports' table
        cursor.execute("INSERT INTO reports (reporter_id, reported_user_id) VALUES (?, ?)",
                       (reporter_id, user_id))
        conn.commit()
        conn.close()

        print("User reported successfully")
        flash('User reported successfully', 'success')
    else:
        print("You have already reported this user")
        flash('You have already reported this user', 'danger')

    return redirect(url_for('user_profile', user_id=user_id))

@app.route("/admin_dashboard")
def admin_dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Fetch user information
    conn = get_db()
    cursor = conn.cursor()

    # Fetch user admin status
    cursor.execute("SELECT is_admin FROM users WHERE email = ?", (session['email'],))
    is_admin = cursor.fetchone()

    # Check if the user is an admin
    if is_admin[0] == 1:
        # Fetch reported users
         
        cursor.execute('''SELECT u.*, r.reporter_id AS reporter_id
                  FROM users u
                  JOIN reports r ON u.id = r.reported_user_id
                  GROUP BY u.id, r.reporter_id''')

        reported_users = cursor.fetchall()
        print(reported_users)

        conn.close()

        return render_template('admin_dashboard.html', reported_users=reported_users)

    else:
        # Redirect regular users
        print("no permission")
        conn.close()
        return redirect(url_for('index'))

# Delete users as admin
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    # Fetch user information
    conn = get_db()
    cursor = conn.cursor()

    # Fetch user admin status
    cursor.execute("SELECT is_admin FROM users WHERE email = ?", (session['email'],))
    is_admin = cursor.fetchone()

    # Check if the user is an admin
    if is_admin[0] == 1:
        # Delete the user and associated reports
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        cursor.execute("DELETE FROM reports WHERE reported_user_id = ?", (user_id,))
        cursor.execute("DELETE FROM items WHERE user_id = ?", (user_id,))
        conn.commit()

        print(f'User with ID {user_id} deleted successfully', 'success')
    else:
        print('You do not have permission to delete users')

    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
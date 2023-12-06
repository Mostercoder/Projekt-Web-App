# Import modules
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, TextAreaField, SelectField, HiddenField
from wtforms.validators import InputRequired, Email, Length, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests
import json

# Create app and configure database
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tellsell.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    average_rating = db.Column(db.Integer, nullable=False, default=0)
    interests = db.Column(db.ARRAY(db.String(255)), nullable=True) #lists different categories
    products = db.relationship('Product', backref='seller', lazy=True)
    bids = db.relationship('Bid', backref='bidder', lazy=True)
    feedbacks_sent = db.relationship('Feedback', backref='sender', lazy='dynamic', foreign_keys='Feedback.sender_id')
    feedbacks_received = db.relationship('Feedback', backref='receiver', lazy='dynamic', foreign_keys='Feedback.receiver_id')
    payments_made = db.relationship('Payment', backref='buyer', lazy='dynamic', foreign_keys='Payment.buyer_id')
    payments_received = db.relationship('Payment', backref='seller', lazy='dynamic', foreign_keys='Payment.seller_id')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.average_rating}')"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_price = db.Column(db.Numeric, nullable=False)
    current_price = db.Column(db.Numeric, nullable=False)
    current_top_bidder_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) #as ctb_user_id
    bid_end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location = db.Column(db.Text, nullable=False) #will be a google maps link
    payment_method = db.Column(db.Boolean, nullable=False) #0=online, 1=in person
    shipping = db.Column(db.Boolean, nullable=False) #shipping available or not
    shipping_cost = db.Column(db.Numeric, nullable=False) #will need to be converted into a standard. will be added to the normal price for UX
    categories = db.relationship('Category', secondary='item_categories', lazy='subquery', backref=db.backref('products', lazy=True))
    bids = db.relationship('Bid', backref='product', lazy=True)
    feedbacks = db.relationship('Feedback', backref='product', lazy=True)
    payments = db.relationship('Payment', backref='product', lazy=True)

    def __repr__(self):
        return f"Product('{self.title}', '{self.owner_user_id}', '{self.current_price}', '{self.bid_end_time}')"

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    bid_amount = db.Column(db.Numeric, nullable=False)
    bid_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Bid('{self.item_id}', '{self.user_id}', '{self.bid_amount}', '{self.bid_time}')"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    transaction_amount = db.Column(db.Numeric, nullable=False)
    transaction_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Transaction('{self.item_id}', '{self.seller_id}', '{self.buyer_id}', '{self.transaction_amount}', '{self.transaction_time}')"

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"Category('{self.name}', '{self.description}')"

class ItemCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        return f"ItemCategory('{self.item_id}', '{self.category_id}')"

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Review('{self.user_id}', '{self.transaction_id}', '{self.rating}', '{self.comment}')"

# Create database forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=255)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=255)])
    remember = BooleanField('Remember me')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=255)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=255)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=255)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password', message='Passwords must match')])

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=255)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=255)])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    interests = SelectMultipleField('Interests', choices=[(c.name, c.name) for c in Category.query.all()]) #lists different categories
    submit = SubmitField('Update')

class CreateProductForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[InputRequired()])
    start_price = DecimalField('Starting Price', validators=[InputRequired(), NumberRange(min=0)])
    bid_end_time = DateTimeField('Bid End Time', validators=[InputRequired()])
    location = StringField('Location', validators=[InputRequired(), Length(max=255)])
    payment_method = BooleanField('Payment Method', validators=[InputRequired()]) #0=online, 1=in person
    shipping = BooleanField('Shipping', validators=[InputRequired()]) #shipping available or not
    shipping_cost = DecimalField('Shipping Cost', validators=[InputRequired(), NumberRange(min=0)])
    categories = SelectMultipleField('Categories', choices=[(c.name, c.name) for c in Category.query.all()])
    submit = SubmitField('Create')

class EditProductForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[InputRequired()])
    start_price = DecimalField('Starting Price', validators=[InputRequired(), NumberRange(min=0)])
    bid_end_time = DateTimeField('Bid End Time', validators=[InputRequired()])
    location = StringField('Location', validators=[InputRequired(), Length(max=255)])
    payment_method = BooleanField('Payment Method', validators=[InputRequired()]) #0=online, 1=in person
    shipping = BooleanField('Shipping', validators=[InputRequired()]) #shipping available or not
    shipping_cost = DecimalField('Shipping Cost', validators=[InputRequired(), NumberRange(min=0)])
    categories = SelectMultipleField('Categories', choices=[(c.name, c.name) for c in Category.query.all()])
    submit = SubmitField('Edit')
    delete = SubmitField('Delete')

class PlaceBidForm(FlaskForm):
    bid_amount = DecimalField('Bid Amount', validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Place Bid')

class LeaveFeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], validators=[InputRequired()])
    comment = TextAreaField('Comment', validators=[InputRequired()])
    submit = SubmitField('Leave Feedback')

# Load user function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/')
def home():
    # Get recommended products based on user's interests and popularity
    if current_user.is_authenticated:
        interests = current_user.interests
        recommended_products = Product.query.filter(Product.category.any(Category.name.in_(interests))).order_by(Product.current_price.desc()).limit(10).all()
    else:
        recommended_products = Product.query.order_by(Product.current_price.desc()).limit(10).all()
    return render_template('home.html', recommended_products=recommended_products)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created. You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.picture = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.interests = form.interests.data
        db.session.commit()
        flash('Your account has been updated', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.interests.data = current_user.interests
    image_file = url_for('static', filename='profile_pics/' + current_user.picture)
    return render_template('profile.html', image_file=image_file, form=form)

# Create product route
@app.route('/create_product', methods=['GET', 'POST'])
@login_required
def create_product():
    form = CreateProductForm()
    if form.validate_on_submit():
        product = Product(owner_user_id=current_user.id, title=form.title.data, description=form.description.data, start_price=form.start_price.data, current_price=form.start_price.data, bid_end_time=form.bid_end_time.data, location=form.location.data, payment_method=form.payment_method.data, shipping=form.shipping.data, shipping_cost=form.shipping_cost.data)
        for category in form.categories.data:
            c = Category.query.filter_by(name=category).first()
            product.categories.append(c)
        db.session.add(product)
        db.session.commit()
        flash('Your product has been created', 'success')
        return redirect(url_for('home'))
    return render_template('create_product.html', form=form)

# Edit product route
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller != current_user:
        abort(403)
    form = EditProductForm()
    if form.validate_on_submit():
        product.title = form.title.data
        product.description = form.description.data
        product.start_price = form.start_price.data
        product.current_price = form.start_price.data
        product.bid_end_time = form.bid_end_time.data
        product.location = form.location.data
        product.payment_method = form.payment_method.data
        product.shipping = form.shipping.data
        product.shipping_cost = form.shipping_cost.data
        product.categories.clear()
        for category in form.categories.data:
            c = Category.query.filter_by(name=category).first()
            product.categories.append(c)
        db.session.commit()
        flash('Your product has been updated', 'success')
        return redirect(url_for('product_details', product_id=product.id))
    elif request.method == 'GET':
        form.title.data = product.title
        form.description.data = product.description
        form.start_price.data = product.start_price
        form.bid_end_time.data = product.bid_end_time
        form.location.data = product.location
        form.payment_method.data = product.payment_method
        form.shipping.data = product.shipping
        form.shipping_cost.data = product.shipping_cost
        form.categories.data = [c.name for c in product.categories]
    return render_template('edit_product.html', form=form)

# Delete product route
@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller != current_user:
        abort(403)
    db.session.delete(product)
    db.session.commit()
    flash('Your product has been deleted', 'success')
    return redirect(url_for('home'))

# Product details route
@app.route('/product_details/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    bids = Bid.query.filter_by(item_id=product.id).order_by(Bid.bid_amount.desc()).all()
    feedbacks = Feedback.query.filter_by(product_id=product.id).order_by(Feedback.created_at.desc()).all()
    form = PlaceBidForm()
    return render_template('product_details.html', product=product, bids=bids, feedbacks=feedbacks, form=form)

# Place bid route
@app.route('/place_bid/<int:product_id>', methods=['POST'])
@login_required
def place_bid(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller == current_user:
        flash('You cannot bid on your own product', 'danger')
        return redirect(url_for('product_details', product_id=product.id))
    if product.status != 'active':
        flash('This product is not available for bidding', 'danger')
        return redirect(url_for('product_details', product_id=product.id))
    if datetime.utcnow() > product.bid_end_time:
        flash('This product has expired', 'danger')
        return redirect(url_for('product_details', product_id=product.id))
    form = PlaceBidForm()
    if form.validate_on_submit():
        bid_amount = form.bid_amount.data
        if bid_amount <= product.current_price:
            flash('Your bid must be higher than the current price', 'danger')
            return redirect(url_for('product_details', product_id=product.id))
        bid = Bid(user_id=current_user.id, item_id=product.id, bid_amount=bid_amount)
        product.current_price = bid_amount
        product.current_top_bidder_user_id = current_user.id
        db.session.add(bid)
        db.session.commit()
        flash('Your bid has been placed', 'success')
        return redirect(url_for('product_details', product_id=product.id))
    return render_template('product_details.html', product=product, form=form)

# Search route
@app.route('/search')
def search():
    query = request.args.get('query')
    if query:
        products = Product.query.filter(Product.title.ilike(f'%{query}%')).order_by(Product.current_price.desc()).all()
    else:
        products = Product.query.order_by(Product.current_price.desc()).all()
    return render_template('search.html', products=products, query=query)

# Category route
@app.route('/category/<string:category_name>')
def category(category_name):
    category = Category.query.filter_by(name=category_name).first_or_404()
    products = category.products
    return render_template('category.html', category=category, products=products)

# Feedback route
@app.route('/feedback/<int:product_id>', methods=['GET', 'POST'])
@login_required
def feedback(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller == current_user:
        receiver = User.query.get(product.current_top_bidder_user_id)
    elif product.current_top_bidder_user_id == current_user.id:
        receiver = product.seller
    else:
        abort(403)
    form = LeaveFeedbackForm()
    if form.validate_on_submit():
        rating = form.rating.data
        comment = form.comment.data
        feedback = Feedback(sender_id=current_user.id, receiver_id=receiver.id, product_id=product.id, rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
        flash('Your feedback has been submitted', 'success')
        return redirect(url_for('product_details', product_id=product.id))
    return render_template('feedback.html', form=form, product=product, receiver=receiver)

# Error handlers
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html'), 500

# Run app
if __name__ == '__main__':
    app.run(debug=True)

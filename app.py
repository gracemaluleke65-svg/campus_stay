import os
import stripe
import json
import random
import traceback
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from config import Config
from models import db, User, Accommodation, Booking, Review, Favorite
from forms import RegistrationForm, LoginForm, AccommodationForm, BookingForm, ReviewForm, SearchForm

# Initialize Flask app
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/campusstay.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('CampusStay startup')

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Configure Stripe
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'images', 'team'), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('range_stars')
def range_stars(rating):
    return range(int(rating))

@app.template_filter('range_empty_stars')
def range_empty_stars(rating):
    return range(5 - int(rating))

def get_amenity_icon(amenity):
    icons = {
        'wifi': 'bi-wifi',
        'parking': 'bi-car-front',
        'laundry': 'bi-water',
        'gym': 'bi-bicycle',
        'furnished': 'bi-house-door',
        'security': 'bi-shield-check',
        'pool': 'bi-droplet',
        'study_area': 'bi-book'
    }
    return icons.get(amenity, 'bi-check')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def seed_admin():
    with app.app_context():
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin:
            admin = User(
                full_name='System Admin',
                email=app.config['ADMIN_EMAIL'],
                student_number='00000000',
                id_number='0000000000000',
                phone='0000000000',
                is_admin=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            app.logger.info('Admin user created successfully')

@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f'404 Error: {error}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'500 Error: {error}\n{traceback.format_exc()}')
    return render_template('500.html'), 500

@app.route('/')
def index():
    try:
        featured = Accommodation.query.filter_by(is_active=True).order_by(db.func.random()).limit(3).all()
        return render_template('index.html', featured=featured, get_amenity_icon=get_amenity_icon)
    except Exception as e:
        app.logger.error(f'Error in index route: {e}')
        return render_template('index.html', featured=[], get_amenity_icon=get_amenity_icon)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                full_name=form.full_name.data,
                email=form.email.data,
                student_number=form.student_number.data,
                id_number=form.id_number.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            app.logger.info(f'New user registered: {user.email}')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {e}')
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                app.logger.info(f'User logged in: {user.email}')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
                app.logger.warning(f'Failed login attempt for email: {form.email.data}')
        except Exception as e:
            app.logger.error(f'Login error: {e}')
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/accommodations', methods=['GET', 'POST'])
def accommodations():
    form = SearchForm()
    query = Accommodation.query.filter_by(is_active=True)
    
    if request.method == 'POST' and form.validate_on_submit():
        if form.location.data:
            query = query.filter(Accommodation.location.ilike(f'%{form.location.data}%'))
        if form.min_price.data:
            query = query.filter(Accommodation.price_per_month >= form.min_price.data)
        if form.max_price.data:
            query = query.filter(Accommodation.price_per_month <= form.max_price.data)
    
    accommodations = query.all()
    
    user_favorites = []
    if current_user.is_authenticated:
        user_favorites = [f.accommodation_id for f in current_user.favorites]
    
    return render_template('accommodations.html', accommodations=accommodations, form=form, 
                         get_amenity_icon=get_amenity_icon, user_favorites=user_favorites)

@app.route('/accommodation/<int:id>')
def accommodation_detail(id):
    try:
        acc = Accommodation.query.get_or_404(id)
        if not acc.is_active:
            flash('This accommodation is no longer available.', 'warning')
            return redirect(url_for('accommodations'))
        
        booking_form = BookingForm()
        review_form = ReviewForm()
        
        has_booked = False
        can_review = False
        existing_review = None
        is_favorite = False
        
        if current_user.is_authenticated:
            has_booked = Booking.query.filter_by(
                user_id=current_user.id, 
                accommodation_id=id, 
                status='paid'
            ).first() is not None
            
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                accommodation_id=id
            ).first()
            
            is_favorite = Favorite.query.filter_by(
                user_id=current_user.id,
                accommodation_id=id
            ).first() is not None
            
            can_review = has_booked and not existing_review
        
        return render_template('accommodation_detail.html', 
                             accommodation=acc, 
                             booking_form=booking_form,
                             review_form=review_form,
                             can_review=can_review,
                             existing_review=existing_review,
                             is_favorite=is_favorite,
                             get_amenity_icon=get_amenity_icon)
    except Exception as e:
        app.logger.error(f'Error in accommodation_detail: {e}')
        flash('Error loading accommodation details.', 'danger')
        return redirect(url_for('accommodations'))

@app.route('/favorite/toggle/<int:accommodation_id>', methods=['POST'])
@login_required
def toggle_favorite(accommodation_id):
    try:
        favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id
        ).first()
        
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            app.logger.info(f'User {current_user.id} removed favorite {accommodation_id}')
            return jsonify({'status': 'removed'})
        else:
            favorite = Favorite(
                user_id=current_user.id,
                accommodation_id=accommodation_id
            )
            db.session.add(favorite)
            db.session.commit()
            app.logger.info(f'User {current_user.id} added favorite {accommodation_id}')
            return jsonify({'status': 'added'})
    except Exception as e:
        app.logger.error(f'Error toggling favorite: {e}')
        return jsonify({'status': 'error'}), 500

@app.route('/favorites')
@login_required
def favorites():
    try:
        user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        accommodation_ids = [f.accommodation_id for f in user_favorites]
        
        if accommodation_ids:
            accommodations = Accommodation.query.filter(
                Accommodation.id.in_(accommodation_ids), 
                Accommodation.is_active==True
            ).all()
        else:
            accommodations = []
        
        fav_ids = [f.accommodation_id for f in current_user.favorites]
        
        return render_template('favorites.html', accommodations=accommodations, 
                             get_amenity_icon=get_amenity_icon, user_favorites=fav_ids)
    except Exception as e:
        app.logger.error(f'Error loading favorites: {e}')
        flash('Error loading favorites.', 'danger')
        return redirect(url_for('index'))

@app.route('/book/<int:accommodation_id>', methods=['POST'])
@login_required
def book(accommodation_id):
    try:
        accommodation = Accommodation.query.get_or_404(accommodation_id)
        
        if accommodation.is_full():
            flash('Sorry, this accommodation is fully booked.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        duration = request.form.get('duration')
        if duration == 'annual':
            months = 10
        else:
            months = 5
        
        total_price = accommodation.price_per_month * months
        
        # Validate minimum amount (Stripe requires at least 50 cents)
        if total_price < 0.5:
            flash('Total price must be at least R 0.50', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        booking = Booking(
            user_id=current_user.id,
            accommodation_id=accommodation_id,
            duration=duration,
            months=months,
            total_price=total_price,
            status='approved'
        )
        db.session.add(booking)
        db.session.commit()
        
        try:
            app.logger.info(f"Creating Stripe checkout session for booking {booking.id}")
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'zar',
                        'unit_amount': int(total_price * 100),
                        'product_data': {
                            'name': f'{accommodation.title}',
                            'description': f'{duration.capitalize()} booking ({months} months) - {accommodation.room_type} room',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('payment_cancel', booking_id=booking.id, _external=True),
            )
            
            booking.stripe_session_id = checkout_session.id
            db.session.commit()
            
            app.logger.info(f"Checkout session created: {checkout_session.id}")
            
            return redirect(checkout_session.url)
        
        except Exception as e:
            app.logger.error(f'Stripe Error: {str(e)}\n{traceback.format_exc()}')
            db.session.delete(booking)
            db.session.commit()
            flash(f'Payment setup failed. Please try again.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
            
    except Exception as e:
        app.logger.error(f'Booking error: {e}')
        flash('An error occurred during booking. Please try again.', 'danger')
        return redirect(url_for('accommodation_detail', id=accommodation_id))

@app.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Invalid payment session.', 'danger')
        return redirect(url_for('index'))
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            booking = Booking.query.filter_by(stripe_session_id=session_id).first()
            if booking:
                booking.status = 'paid'
                
                accommodation = Accommodation.query.get(booking.accommodation_id)
                accommodation.current_occupancy += 1
                if accommodation.current_occupancy >= accommodation.capacity:
                    accommodation.is_active = False
                
                db.session.commit()
                
                app.logger.info(f'Payment successful for booking {booking.id}')
                flash('Payment successful! Please leave a review.', 'success')
                return render_template('payment_success.html', accommodation_id=booking.accommodation_id)
    except Exception as e:
        app.logger.error(f"Payment verification error: {str(e)}")
        flash('Payment verification failed.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/payment/cancel/<int:booking_id>')
def payment_cancel(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.status == 'approved':
            booking.status = 'cancelled'
            db.session.commit()
            app.logger.info(f'Payment cancelled for booking {booking_id}')
        flash('Payment cancelled.', 'info')
        return render_template('payment_cancel.html')
    except Exception as e:
        app.logger.error(f'Payment cancel error: {e}')
        flash('Error processing cancellation.', 'danger')
        return redirect(url_for('index'))

@app.route('/review/<int:accommodation_id>', methods=['POST'])
@login_required
def submit_review(accommodation_id):
    try:
        booking = Booking.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id,
            status='paid'
        ).first()
        
        if not booking:
            flash('You can only review accommodations you have booked and paid for.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        existing = Review.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id
        ).first()
        
        if existing:
            flash('You have already reviewed this accommodation.', 'warning')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        form = ReviewForm()
        if form.validate_on_submit():
            review = Review(
                user_id=current_user.id,
                accommodation_id=accommodation_id,
                rating=int(form.rating.data),
                comment=form.comment.data
            )
            db.session.add(review)
            db.session.commit()
            app.logger.info(f'Review submitted by user {current_user.id} for accommodation {accommodation_id}')
            flash('Review submitted successfully!', 'success')
        
        return redirect(url_for('accommodation_detail', id=accommodation_id))
    except Exception as e:
        app.logger.error(f'Review submission error: {e}')
        flash('Error submitting review.', 'danger')
        return redirect(url_for('accommodation_detail', id=accommodation_id))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        stats = {
            'total_users': User.query.count(),
            'total_accommodations': Accommodation.query.count(),
            'active_accommodations': Accommodation.query.filter_by(is_active=True).count(),
            'total_bookings': Booking.query.count(),
            'paid_bookings': Booking.query.filter_by(status='paid').count(),
            'total_revenue': db.session.query(db.func.sum(Booking.total_price)).filter_by(status='paid').scalar() or 0
        }
        
        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        app.logger.error(f'Admin dashboard error: {e}')
        flash('Error loading dashboard.', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/accommodation/new', methods=['GET', 'POST'])
@login_required
def admin_new_accommodation():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    form = AccommodationForm()
    if form.validate_on_submit():
        try:
            acc = Accommodation(
                title=form.title.data,
                description=form.description.data,
                location=form.location.data,
                room_type=form.room_type.data,
                price_per_month=form.price_per_month.data,
                capacity=form.capacity.data,
                current_occupancy=form.current_occupancy.data,
                admin_id=current_user.id
            )
            
            amenities = []
            if form.wifi.data == '1': amenities.append('wifi')
            if form.parking.data == '1': amenities.append('parking')
            if form.laundry.data == '1': amenities.append('laundry')
            if form.gym.data == '1': amenities.append('gym')
            if form.furnished.data == '1': amenities.append('furnished')
            if form.security.data == '1': amenities.append('security')
            if form.pool.data == '1': amenities.append('pool')
            if form.study_area.data == '1': amenities.append('study_area')
            acc.set_amenities_list(amenities)
            
            if form.image.data:
                filename = secure_filename(form.image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                acc.image_filename = filename
            
            db.session.add(acc)
            db.session.commit()
            app.logger.info(f'New accommodation created by admin {current_user.id}: {acc.title}')
            flash('Accommodation added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating accommodation: {e}')
            flash('Error adding accommodation. Please try again.', 'danger')
    
    return render_template('admin/accommodation_form.html', form=form, title='New Accommodation')

@app.route('/admin/accommodation/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_accommodation(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        acc = Accommodation.query.get_or_404(id)
        form = AccommodationForm(obj=acc)
        
        if form.validate_on_submit():
            acc.title = form.title.data
            acc.description = form.description.data
            acc.location = form.location.data
            acc.room_type = form.room_type.data
            acc.price_per_month = form.price_per_month.data
            acc.capacity = form.capacity.data
            acc.current_occupancy = form.current_occupancy.data
            
            amenities = []
            if form.wifi.data == '1': amenities.append('wifi')
            if form.parking.data == '1': amenities.append('parking')
            if form.laundry.data == '1': amenities.append('laundry')
            if form.gym.data == '1': amenities.append('gym')
            if form.furnished.data == '1': amenities.append('furnished')
            if form.security.data == '1': amenities.append('security')
            if form.pool.data == '1': amenities.append('pool')
            if form.study_area.data == '1': amenities.append('study_area')
            acc.set_amenities_list(amenities)
            
            if form.image.data:
                if acc.image_filename:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], acc.image_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(form.image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                acc.image_filename = filename
            
            db.session.commit()
            app.logger.info(f'Accommodation {id} updated by admin {current_user.id}')
            flash('Accommodation updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        current_amenities = acc.get_amenities_list()
        form.wifi.data = '1' if 'wifi' in current_amenities else '0'
        form.parking.data = '1' if 'parking' in current_amenities else '0'
        form.laundry.data = '1' if 'laundry' in current_amenities else '0'
        form.gym.data = '1' if 'gym' in current_amenities else '0'
        form.furnished.data = '1' if 'furnished' in current_amenities else '0'
        form.security.data = '1' if 'security' in current_amenities else '0'
        form.pool.data = '1' if 'pool' in current_amenities else '0'
        form.study_area.data = '1' if 'study_area' in current_amenities else '0'
        
        return render_template('admin/accommodation_form.html', form=form, title='Edit Accommodation')
    except Exception as e:
        app.logger.error(f'Error editing accommodation {id}: {e}')
        flash('Error loading accommodation for editing.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/accommodation/<int:id>/delete', methods=['POST'])
@login_required
def admin_delete_accommodation(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        acc = Accommodation.query.get_or_404(id)
        
        if acc.image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], acc.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(acc)
        db.session.commit()
        app.logger.info(f'Accommodation {id} deleted by admin {current_user.id}')
        flash('Accommodation deleted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting accommodation {id}: {e}')
        flash('Error deleting accommodation.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        app.logger.error(f'Error loading users: {e}')
        flash('Error loading users.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:id>/promote', methods=['POST'])
@login_required
def admin_promote_user(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('You cannot modify your own admin status.', 'warning')
            return redirect(url_for('admin_users'))
        
        user.is_admin = True
        db.session.commit()
        app.logger.info(f'User {id} promoted to admin by {current_user.id}')
        flash(f'{user.full_name} is now an admin.', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error promoting user {id}: {e}')
        flash('Error promoting user.', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:id>/demote', methods=['POST'])
@login_required
def admin_demote_user(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('You cannot modify your own admin status.', 'warning')
            return redirect(url_for('admin_users'))
        
        user.is_admin = False
        db.session.commit()
        app.logger.info(f'User {id} demoted from admin by {current_user.id}')
        flash(f'{user.full_name} is no longer an admin.', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error demoting user {id}: {e}')
        flash('Error demoting user.', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        return render_template('admin/bookings.html', bookings=bookings)
    except Exception as e:
        app.logger.error(f'Error loading bookings: {e}')
        flash('Error loading bookings.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/team')
def team_page():
    return render_template('team.html')

@app.route('/my-bookings')
@login_required
def my_bookings():
    try:
        bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
        return render_template('my_bookings.html', bookings=bookings)
    except Exception as e:
        app.logger.error(f'Error loading user bookings for {current_user.id}: {e}')
        flash('Error loading your bookings.', 'danger')
        return redirect(url_for('index'))

# Create database tables and seed admin
with app.app_context():
    try:
        db.create_all()
        seed_admin()
        app.logger.info('Database initialized successfully')
    except Exception as e:
        app.logger.error(f'Database initialization error: {e}')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
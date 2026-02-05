from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    student_number = db.Column(db.String(8), unique=True, nullable=False)
    id_number = db.Column(db.String(13), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    reviews = db.relationship('Review', backref='user', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Accommodation(db.Model):
    __tablename__ = 'accommodation'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # single, shared, double, suite, apartment
    price_per_month = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, default=0)
    amenities = db.Column(db.Text)  # JSON stored as text
    image_filename = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    bookings = db.relationship('Booking', backref='accommodation', lazy='dynamic')
    reviews = db.relationship('Review', backref='accommodation', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='accommodation', lazy='dynamic')
    
    def get_amenities_list(self):
        if self.amenities:
            return json.loads(self.amenities)
        return []
    
    def set_amenities_list(self, amenities_list):
        self.amenities = json.dumps(amenities_list)
    
    def is_full(self):
        return self.current_occupancy >= self.capacity
    
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(r.rating for r in reviews) / len(reviews)
    
    def __repr__(self):
        return f'<Accommodation {self.title}>'

class Booking(db.Model):
    __tablename__ = 'booking'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    duration = db.Column(db.String(20), nullable=False)  # semester, annual
    months = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='approved')  # approved, paid, cancelled
    stripe_session_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Booking {self.id}>'

class Review(db.Model):
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Review {self.id}>'

class Favorite(db.Model):
    __tablename__ = 'favorite'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Favorite {self.id}>'
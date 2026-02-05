from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, IntegerField, TextAreaField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
from models import User

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    student_number = StringField('Student Number (8 digits)', validators=[DataRequired(), Length(min=8, max=8)])
    id_number = StringField('ID Number (13 digits)', validators=[DataRequired(), Length(min=13, max=13)])
    phone = StringField('Phone Number (10 digits)', validators=[DataRequired(), Length(min=10, max=10)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_student_number(self, field):
        if not field.data.isdigit():
            raise ValidationError('Student number must contain only digits.')
        user = User.query.filter_by(student_number=field.data).first()
        if user:
            raise ValidationError('Student number already registered.')
    
    def validate_id_number(self, field):
        if not field.data.isdigit():
            raise ValidationError('ID number must contain only digits.')
        user = User.query.filter_by(id_number=field.data).first()
        if user:
            raise ValidationError('ID number already registered.')
    
    def validate_phone(self, field):
        if not field.data.isdigit():
            raise ValidationError('Phone number must contain only digits.')
        user = User.query.filter_by(phone=field.data).first()
        if user:
            raise ValidationError('Phone number already registered.')
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AccommodationForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    location = StringField('Location', validators=[DataRequired(), Length(max=200)])
    room_type = SelectField('Room Type', choices=[
        ('single', 'Single Room'),
        ('shared', 'Shared Room'),
        ('double', 'Double Room'),
        ('suite', 'Suite'),
        ('apartment', 'Apartment')
    ], validators=[DataRequired()])
    price_per_month = FloatField('Price Per Month', validators=[DataRequired(), NumberRange(min=0)])
    capacity = IntegerField('Total Capacity', validators=[DataRequired(), NumberRange(min=1)])
    current_occupancy = IntegerField('Current Occupancy', validators=[NumberRange(min=0)], default=0)
    image = FileField('Accommodation Image')
    wifi = SelectField('WiFi', choices=[('0', 'No'), ('1', 'Yes')])
    parking = SelectField('Parking', choices=[('0', 'No'), ('1', 'Yes')])
    laundry = SelectField('Laundry', choices=[('0', 'No'), ('1', 'Yes')])
    gym = SelectField('Gym', choices=[('0', 'No'), ('1', 'Yes')])
    furnished = SelectField('Furnished', choices=[('0', 'No'), ('1', 'Yes')])
    security = SelectField('Security', choices=[('0', 'No'), ('1', 'Yes')])
    pool = SelectField('Swimming Pool', choices=[('0', 'No'), ('1', 'Yes')])
    study_area = SelectField('Study Area', choices=[('0', 'No'), ('1', 'Yes')])
    submit = SubmitField('Save Accommodation')

class BookingForm(FlaskForm):
    duration = SelectField('Duration', choices=[
        ('semester', 'Semester (5 months)'),
        ('annual', 'Annual (10 months)')
    ], validators=[DataRequired()])
    submit = SubmitField('Proceed to Payment')

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '5 Stars'),
        ('4', '4 Stars'),
        ('3', '3 Stars'),
        ('2', '2 Stars'),
        ('1', '1 Star')
    ], validators=[DataRequired()])
    comment = TextAreaField('Comment (Optional)')
    submit = SubmitField('Submit Review')

class SearchForm(FlaskForm):
    location = StringField('Location')
    min_price = FloatField('Min Price')
    max_price = FloatField('Max Price')
    submit = SubmitField('Search')
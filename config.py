import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Secret key for session management (from environment)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration - Render PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///accommodation.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pooling for PostgreSQL
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'max_overflow': 20,
        }
    
    # Upload folder for accommodation images
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Stripe Keys (from environment)
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
    
    # Admin seed (from environment)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@campusstay.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Debug mode (should be False in production)
    DEBUG = os.environ.get('FLASK_ENV') != 'production'
    
    # Logging
    LOG_LEVEL = 'INFO'
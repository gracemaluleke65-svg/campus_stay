# setup_db.py
import os
from app import app, db
from models import User
from config import Config

def setup_database():
    """Initialize the database with tables and admin user"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if not exists
        admin_email = Config.ADMIN_EMAIL
        admin_password = Config.ADMIN_PASSWORD
        
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                full_name='System Admin',
                email=admin_email,
                student_number='00000000',
                id_number='0000000000000',
                phone='0000000000',
                is_admin=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print('✅ Admin user created successfully')
        else:
            print('✅ Admin user already exists')
        
        print('✅ Database setup completed')

if __name__ == '__main__':
    setup_database()
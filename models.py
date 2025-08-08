from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(300))
    occupation = db.Column(db.String(120))
    profile_photo = db.Column(db.String(300))
    password_hash = db.Column(db.String(300))

    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(128), nullable=True)
    reset_password_token = db.Column(db.String(128), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_email_verification_token(self):
        token = secrets.token_urlsafe(64)
        self.email_verification_token = token
        return token

    def generate_reset_password_token(self):
        token = secrets.token_urlsafe(64)
        self.reset_password_token = token
        self.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
        return token

    def verify_reset_token(self, token):
        return (
            token == self.reset_password_token
            and self.reset_token_expiration
            and datetime.utcnow() < self.reset_token_expiration
        )

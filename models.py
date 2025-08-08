from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(300))
    occupation = db.Column(db.String(120))
    profile_photo = db.Column(db.String(300))
    password_hash = db.Column(db.String(300))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

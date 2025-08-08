from flask import session
from models import User

def login_user(user):
    session.permanent = True
    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_email"] = user.email
    session["user_photo"] = user.profile_photo

def logout_user():
    session.clear()

def current_user():
    uid = session.get("user_id")
    if uid:
        return User.query.get(uid)
    return None

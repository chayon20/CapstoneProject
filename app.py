import os
from datetime import timedelta
from functools import wraps
from flask_mail import Mail, Message
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from config import SECRET_KEY, UPLOAD_FOLDER, SQLALCHEMY_DATABASE_URI
from models import db, User
from auth import login_user, logout_user, current_user
from predict import predict_rice_disease
from nutrients import analyze_nutrient_level, random_soil_data
from disease_solutions import disease_solutions

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.permanent_session_lifetime = timedelta(days=7)

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='pronab017das@gmail.com',
    MAIL_PASSWORD=''
)

mail = Mail(app)


db.init_app(app)
with app.app_context():
    db.create_all()

def login_required(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please login to access this page.", "error")
            return redirect(url_for("login"))
        return route_func(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template("home.html", user=current_user())

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        address = request.form.get("address", "").strip()
        occupation = request.form.get("occupation", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm]):
            flash("Please fill required fields", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        file = request.files.get("profile_photo")
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_user = User(
            name=name,
            email=email,
            address=address,
            occupation=occupation,
            profile_photo=filename,
            password_hash=generate_password_hash(password),
            email_verified=False  # new field
        )

        # Generate email verification token before committing
        token = new_user.generate_email_verification_token()

        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for("register"))

        # Send verification email
        verify_url = url_for('verify_email', token=token, _external=True)
        msg = Message(
            subject="Verify Your Email - RiceHealth",
            sender=app.config['MAIL_USERNAME'],
            recipients=[new_user.email],
            body=f"Hi {new_user.name},\n\nPlease verify your email by clicking the link below:\n{verify_url}\n\nIf you did not sign up, please ignore this email."
        )
        try:
            mail.send(msg)
            flash("Registration successful! Please check your email to verify your account.", "success")
        except Exception as e:
            flash(f"Registration successful, but verification email could not be sent: {e}", "warning")

        return redirect(url_for("login"))

    return render_template("register.html", user=current_user())


@app.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if not user:
        flash("Invalid or expired verification token.", "error")
        return redirect(url_for('login'))

    user.email_verified = True
    user.email_verification_token = None
    db.session.commit()
    flash("Email verified successfully! You can now login.", "success")
    return redirect(url_for('login'))




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with that email. Please register.", "error")
            return redirect(url_for("register"))

        if not user.check_password(password):
            flash("Password incorrect. Try again.", "error")
            return redirect(url_for("login"))

        # Check if email is verified
        if not user.email_verified:
            flash("Please verify your email before logging in. Check your inbox.", "warning")
            return redirect(url_for("login"))

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("index"))

    return render_template("login.html", user=current_user())



@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account with that email found.", "error")
            return redirect(url_for('forgot_password'))

        token = user.generate_reset_password_token()
        db.session.commit()
        reset_url = url_for('reset_password', token=token, _external=True)

        msg = Message(
            subject="Password Reset Request - RiceHealth",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email],
            body=f"Hi {user.name},\n\nTo reset your password, click the following link:\n{reset_url}\n\nIf you didn't request this, ignore this email."
        )
        try:
            mail.send(msg)
            flash("Password reset instructions sent to your email.", "info")
        except Exception as e:
            flash(f"Failed to send email: {e}", "error")
        return redirect(url_for('login'))

    return render_template('forgot_password.html', user=current_user())


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_password_token=token).first()
    if not user or not user.verify_reset_token(token):
        flash("Invalid or expired password reset token.", "error")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if not password or password != confirm:
            flash("Passwords do not match or are empty.", "error")
            return redirect(url_for('reset_password', token=token))

        user.password_hash = generate_password_hash(password)
        user.reset_password_token = None
        user.reset_token_expiration = None
        db.session.commit()
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', user=current_user(), token=token)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        occupation = request.form.get('occupation', '').strip()
        file = request.files.get('profile_photo')

        if name:
            user.name = name
        user.address = address
        user.occupation = occupation

        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            user.profile_photo = filename

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)



@app.route("/logout")
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/profile")
def profile():
    user = current_user()
    if not user:
        flash("Please login to view profile.", "error")
        return redirect(url_for("login"))
    return render_template("profile.html", user=user)

@app.route("/rice-disease", methods=["GET", "POST"])
@login_required
def rice_disease():
    prediction = None
    confidence = None
    solution = None
    filename = None
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            flash("Please choose an image.", "error")
            return redirect(url_for("rice_disease"))
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        try:
            prediction, confidence = predict_rice_disease(save_path)
            solution = disease_solutions.get(prediction)
        except Exception as e:
            flash(f"Prediction error: {e}", "error")
            return redirect(url_for("rice_disease"))

    return render_template(
        "rice_disease.html",
        user=current_user(),
        prediction=prediction,
        confidence=confidence,
        solution=solution,
        filename=filename,
    )

@app.route("/soil-test")
@login_required
def soil_test():
    return render_template("soil_test.html", user=current_user())

@app.route("/soil-data")
def soil_data():
    return jsonify(random_soil_data())

@app.route("/soil-report", methods=["GET", "POST"])
def soil_report():
    report = {}
    nitrogen = phosphorus = potassium = None
    error = None

    if request.method == "POST":
        try:
            nitrogen = float(request.form.get("nitrogen"))
            phosphorus = float(request.form.get("phosphorus"))
            potassium = float(request.form.get("potassium"))
        except (TypeError, ValueError):
            error = "Please enter valid numeric values for all nutrients."

        if not error:
            report["nitrogen"] = analyze_nutrient_level("nitrogen", nitrogen)
            report["phosphorus"] = analyze_nutrient_level("phosphorus", phosphorus)
            report["potassium"] = analyze_nutrient_level("potassium", potassium)

    return render_template(
        "soil_text.html",
        user=current_user(),
        report=report,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
        error=error
    )

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    app.run(debug=True)
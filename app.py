import os
from datetime import timedelta
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

db.init_app(app)
with app.app_context():
    db.create_all()

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
        )
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for("register"))

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", user=current_user())

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

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("index"))
    return render_template("login.html", user=current_user())

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


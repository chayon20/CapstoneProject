from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

# -----------------------------------------------------------------------------
# User table
# -----------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(300))
    occupation = db.Column(db.String(120))
    profile_photo = db.Column(db.String(300))
    password_hash = db.Column(db.String(300))

    # Email + password reset fields
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(128), nullable=True)
    reset_password_token = db.Column(db.String(128), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    # --- Helpers ---
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_email_verification_token(self) -> str:
        token = secrets.token_urlsafe(64)
        self.email_verification_token = token
        return token

    def generate_reset_password_token(self) -> str:
        token = secrets.token_urlsafe(64)
        self.reset_password_token = token
        self.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
        return token

    def verify_reset_token(self, token: str) -> bool:
        return (
            token == self.reset_password_token
            and self.reset_token_expiration
            and datetime.utcnow() < self.reset_token_expiration
        )

# -----------------------------------------------------------------------------
# SensorReading table (for ESP32 sensor data)
# -----------------------------------------------------------------------------
class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # NPK mg/kg
    nitrogen = db.Column(db.Float, nullable=True)
    phosphorus = db.Column(db.Float, nullable=True)
    potassium = db.Column(db.Float, nullable=True)

    # Soil/Env
    moisture = db.Column(db.Float, nullable=True)      # %
    temperature = db.Column(db.Float, nullable=True)   # °C
    humidity = db.Column(db.Float, nullable=True)      # %
    ph = db.Column(db.Float, nullable=True)

    def as_dict(self, moisture_min: int = 35) -> dict:
        """Return a flat dict for JSON serialization (used in soil_test.html)."""
        return {
            "id": self.id,
            "saved_at": (self.created_at.isoformat() + "Z") if self.created_at else None,
            "nitrogen": self.nitrogen,
            "phosphorus": self.phosphorus,
            "potassium": self.potassium,
            "moisture": self.moisture,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "ph": self.ph,
            "moisture_min": moisture_min,
        }

    @staticmethod
    def latest():
        """Get the most recent row (for /soil-data)."""
        return SensorReading.query.order_by(SensorReading.created_at.desc()).first()

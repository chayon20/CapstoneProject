from dataclasses import dataclass
from typing import Dict, Any, Optional

# ---- Nutrient & pH thresholds ----
nutrient_levels: Dict[str, Dict[str, Any]] = {
    "nitrogen": {
        "low": 50,
        "optimal_min": 50,
        "optimal_max": 100,
        "high": 150,
        "symptoms_low": [
            "Yellowing older leaves (chlorosis)",
            "Stunted growth",
            "Poor tillering"
        ],
        "fertilizer_low": "Apply 80–120 kg N/ha (Urea, Ammonium sulfate) in split doses (transplanting, tillering, panicle)",
        "symptoms_high": [
            "Excessive vegetative growth",
            "Delayed maturity",
            "Lodging risk",
            "Poor grain filling"
        ],
        "solution_high": [
            "Reduce nitrogen fertilizer",
            "Balanced fertilization",
            "Avoid excessive irrigation"
        ],
    },
    "phosphorus": {
        "low": 10,
        "optimal_min": 10,
        "optimal_max": 30,
        "high": 50,
        "symptoms_low": [
            "Dark green leaves but poor tillering",
            "Stunted root growth",
            "Delayed maturity"
        ],
        "fertilizer_low": "Apply 30–60 kg P2O5/ha (SSP, TSP, DAP) at transplanting for best uptake",
        "symptoms_high": [
            "Micronutrient (Zn, Fe) deficiencies due to antagonism"
        ],
        "solution_high": [
            "Avoid excessive P application",
            "Soil test before fertilization"
        ],
    },
    "potassium": {
        "low": 80,
        "optimal_min": 80,
        "optimal_max": 200,
        "high": 250,
        "symptoms_low": [
            "Yellowing and drying leaf edges (marginal scorch)",
            "Weak stems and lodging",
            "Poor grain filling and quality"
        ],
        "fertilizer_low": "Apply 40–80 kg K2O/ha (MOP, SOP) split application (transplanting, tillering)",
        "symptoms_high": [],
        "solution_high": [],
    },
    "ph": {
        "low": 5.5,            # acidic threshold
        "optimal_min": 5.5,
        "optimal_max": 7.0,
        "high": 7.5,           # alkaline threshold
        "symptoms_low": [
            "Acidic soil: Poor root growth",
            "Iron/Manganese toxicity",
            "Phosphorus deficiency",
            "Stunted growth"
        ],
        "fertilizer_low": "Apply agricultural lime or dolomite, add compost/organic matter, and use phosphate fertilizers.",
        "symptoms_high": [
            "Alkaline soil: Zinc/Iron deficiency",
            "Yellowing leaves (chlorosis)",
            "Poor tillering",
            "Reduced nutrient uptake"
        ],
        "solution_high": [
            "Apply gypsum or elemental sulfur",
            "Use acid-forming fertilizers (ammonium sulfate, urea)",
            "Grow green manure crops (Sesbania, Dhaincha)"
        ],
    },
}

# ---- Data structure for analysis ----
@dataclass
class NutrientAnalysis:
    status: str
    symptoms_if_low: list
    fertilizer_if_low: str
    symptoms_if_high: list
    solution_if_high: list
    recommendation: str

def analyze_nutrient_level(nutrient: str, value: float) -> Optional[NutrientAnalysis]:
    info = nutrient_levels.get(nutrient)
    if not info:
        return None

    if value < info["low"]:
        status = "Low"
        symptoms = info["symptoms_low"]
        recommendation = info["fertilizer_low"]
        issues_high = []
        solution_high = []
    elif info["optimal_min"] <= value <= info["optimal_max"]:
        status = "Good"
        symptoms = []
        recommendation = f"{nutrient.capitalize()} level is optimal."
        issues_high = []
        solution_high = []
    elif value > info["high"]:
        status = "High"
        symptoms = info.get("symptoms_high", [])
        recommendation = ""
        issues_high = symptoms
        solution_high = info.get("solution_high", [])
    else:
        status = "Slightly High"
        symptoms = []
        recommendation = "Be cautious of potential nutrient imbalance."
        issues_high = []
        solution_high = []

    return NutrientAnalysis(
        status=status,
        symptoms_if_low=info.get("symptoms_low", []),
        fertilizer_if_low=info.get("fertilizer_low", ""),
        symptoms_if_high=symptoms,
        solution_if_high=solution_high,
        recommendation=recommendation,
    )

# ---- Watering helper ----
DEFAULT_MOISTURE_MIN = 35  # %
def moisture_action(moisture_pct: float, min_pct: int = DEFAULT_MOISTURE_MIN) -> str:
    return "Give water" if moisture_pct < min_pct else "Moisture OK"

# ---- Optional DB save helper ----
def save_sensor_row(db, SensorReading, payload: Dict[str, Any]):
    """
    Persist a reading to DB. 'payload' keys:
    nitrogen, phosphorus, potassium, moisture, temperature, humidity, ph
    """
    row = SensorReading(
        nitrogen=payload.get("nitrogen"),
        phosphorus=payload.get("phosphorus"),
        potassium=payload.get("potassium"),
        moisture=payload.get("moisture"),
        temperature=payload.get("temperature"),
        humidity=payload.get("humidity"),
        ph=payload.get("ph"),
    )
    db.session.add(row)
    db.session.commit()
    return row

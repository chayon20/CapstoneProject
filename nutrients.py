import random

nutrient_levels = {
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
        ]
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
        ]
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
        "solution_high": []
    }
}

def analyze_nutrient_level(nutrient, value):
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
        status = "Optimal"
        symptoms = []
        recommendation = "Nutrient level is optimal."
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

    return {
        "status": status,
        "symptoms_if_low": info.get("symptoms_low", []),
        "fertilizer_if_low": info.get("fertilizer_low", ""),
        "symptoms_if_high": symptoms,
        "solution_if_high": solution_high,
        "recommendation": recommendation
    }

def random_soil_data():
    return {
        "nitrogen": round(random.uniform(0, 50), 2),
        "phosphorus": round(random.uniform(0, 50), 2),
        "potassium": round(random.uniform(0, 50), 2),
    }

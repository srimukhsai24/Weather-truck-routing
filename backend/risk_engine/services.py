RISK_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "SEVERE": 3, "NO_TRAVEL": 4}

def classify_threshold(value: float, thresholds: tuple, inclusive: bool = False) -> str:
    """Classify using exclusive bounds for wind and inclusive upper bounds for rain/snow."""
    for index, (upper_bound, level) in enumerate(thresholds):
        matches = value < upper_bound if (not inclusive or index == 0) else value <= upper_bound
        if matches:
            return level
    return "NO_TRAVEL"

def evaluate_checkpoint(weather: dict, load_weight_lb: float) -> dict:
    # Missing forecast data must never be presented as safe weather.
    if not weather.get("forecast_available", True):
        return {"risk_level": "HIGH", "risk_by_condition": {"wind": "HIGH", "rain": "HIGH", "snow": "HIGH"}, "risk_basis": "FORECAST_UNAVAILABLE"}
    wind = weather.get("wind_mph") or 0
    rain = weather.get("rain_in_per_hour") or 0
    snow = weather.get("snow_in_per_hour") or 0
    wind_risk = classify_threshold(wind, ((25, "LOW"), (35, "MODERATE"), (45, "HIGH"), (55, "SEVERE")))
    rain_risk = classify_threshold(rain, ((0.10, "LOW"), (0.25, "MODERATE"), (0.50, "HIGH"), (1.00, "SEVERE")), inclusive=True)
    snow_risk = classify_threshold(snow, ((0.5, "LOW"), (1.0, "MODERATE"), (2.0, "HIGH"), (3.0, "SEVERE")), inclusive=True)
    # Load-specific wind rules override the base weather classification:
    # • ≥55 mph → No Travel for any load
    # • 45–54 mph + >30,000 lb → No Travel
    # • 35–44 mph + >40,000 lb → Severe
    if wind >= 55.0:
        wind_risk = "NO_TRAVEL"
    elif 45.0 <= wind < 55.0 and load_weight_lb > 30000:
        wind_risk = "NO_TRAVEL"
    elif 35.0 <= wind < 45.0 and load_weight_lb > 40000:
        wind_risk = "SEVERE"
    risk_by_condition = {"wind": wind_risk, "rain": rain_risk, "snow": snow_risk}
    overall_risk = max(risk_by_condition.values(), key=lambda level: RISK_ORDER[level])
    return {"risk_level": overall_risk, "risk_by_condition": risk_by_condition}

def summarize_route(checkpoints: list) -> dict:
    miles_by_risk = {level: 0.0 for level in RISK_ORDER}
    weighted_risk = 0.0
    total_miles = 0.0
    for checkpoint in checkpoints:
        miles = checkpoint["segment_miles"]
        level = checkpoint["risk_level"]
        miles_by_risk[level] += miles
        weighted_risk += RISK_ORDER[level] * miles
        total_miles += miles
    return {
        "risk_miles": {level.lower(): round(miles, 2) for level, miles in miles_by_risk.items()},
        "average_risk_score": round(weighted_risk / total_miles, 3) if total_miles else 0,
        "total_miles": round(total_miles, 2),
        "severe_miles": round(miles_by_risk["SEVERE"] + miles_by_risk["NO_TRAVEL"], 2),
        "high_miles": round(miles_by_risk["HIGH"], 2),
        "no_travel_miles": round(miles_by_risk["NO_TRAVEL"], 2),
    }

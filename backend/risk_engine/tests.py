from risk_engine.services import evaluate_checkpoint


def weather(wind=0, rain=0, snow=0):
    return {"wind_mph": wind, "rain_in_per_hour": rain, "snow_in_per_hour": snow}


def test_wind_threshold_boundaries():
    assert evaluate_checkpoint(weather(wind=24.9), 10000)["risk_level"] == "LOW"
    assert evaluate_checkpoint(weather(wind=25), 10000)["risk_level"] == "MODERATE"
    assert evaluate_checkpoint(weather(wind=35), 10000)["risk_level"] == "HIGH"
    assert evaluate_checkpoint(weather(wind=45), 10000)["risk_level"] == "SEVERE"
    assert evaluate_checkpoint(weather(wind=55), 10000)["risk_level"] == "NO_TRAVEL"


def test_rain_and_snow_threshold_boundaries():
    assert evaluate_checkpoint(weather(rain=0.099), 10000)["risk_level"] == "LOW"
    assert evaluate_checkpoint(weather(rain=0.10), 10000)["risk_level"] == "MODERATE"
    assert evaluate_checkpoint(weather(rain=0.25), 10000)["risk_level"] == "HIGH"
    assert evaluate_checkpoint(weather(rain=0.50), 10000)["risk_level"] == "SEVERE"
    assert evaluate_checkpoint(weather(rain=1.01), 10000)["risk_level"] == "NO_TRAVEL"
    assert evaluate_checkpoint(weather(snow=0.5), 10000)["risk_level"] == "MODERATE"
    assert evaluate_checkpoint(weather(snow=3.0), 10000)["risk_level"] == "SEVERE"
    assert evaluate_checkpoint(weather(snow=3.01), 10000)["risk_level"] == "NO_TRAVEL"


def test_load_specific_wind_rules():
    assert evaluate_checkpoint(weather(wind=46), 30000)["risk_level"] == "SEVERE"
    assert evaluate_checkpoint(weather(wind=46), 30001)["risk_level"] == "NO_TRAVEL"
    assert evaluate_checkpoint(weather(wind=40), 40001)["risk_level"] == "SEVERE"
    assert evaluate_checkpoint(weather(wind=54.9), 50000)["risk_level"] == "NO_TRAVEL"


def test_worst_condition_wins():
    result = evaluate_checkpoint(weather(wind=10, rain=0.3, snow=0), 10000)
    assert result["risk_level"] == "HIGH"


def test_missing_forecast_is_not_marked_low_risk():
    missing_weather = {"forecast_available": False}
    result = evaluate_checkpoint(missing_weather, 10000)
    assert result["risk_level"] == "HIGH"
    assert result["risk_basis"] == "FORECAST_UNAVAILABLE"

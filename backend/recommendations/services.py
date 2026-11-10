def rank_routes(routes: list) -> list:
    """
    Apply the assignment's strict recommendation priority:
    1. Fewest Severe miles (including any No-Travel miles)
    2. Fewest High miles
    3. Lowest average risk
    4. Shortest travel times
    """
    ranked = sorted(routes, key=lambda route: (
        route["summary"].get("no_travel_miles", 0.0),
        route["summary"]["severe_miles"],
        route["summary"]["high_miles"],
        route["summary"]["average_risk_score"],
        route["duration_seconds"],
    ))
    for index, route in enumerate(ranked, start=1):
        route["rank"] = index
        route["recommended"] = (index == 1)
    return ranked

def get_recommendation_reason(recommended_route: dict, all_routes: list) -> str:
    summary = recommended_route["summary"]
    severe = summary["severe_miles"]
    high = summary["high_miles"]
    avg = summary["average_risk_score"]
    duration_min = round(recommended_route["duration_seconds"] / 60)
    dur_str = f"{duration_min // 60}h {duration_min % 60}m"

    reasons = []
    if severe == 0 and high == 0:
        reasons.append("Zero severe & high-risk exposure")
    elif severe == 0:
        reasons.append(f"Zero severe miles (only {high:.1f} mi high-risk)")
    else:
        reasons.append(f"Lowest severe exposure ({severe:.1f} mi)")

    reasons.append(f"average risk {avg:.2f}/4")
    reasons.append(f"travel time {dur_str}")

    return f"Ranked #1 by safety-first rules: {', '.join(reasons)}."

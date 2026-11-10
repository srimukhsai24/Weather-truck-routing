from recommendations.services import rank_routes, get_recommendation_reason


def test_recommendation_ranking_priority():
    # Route A: Fast but has 5 severe miles
    route_a = {
        "id": "A",
        "name": "Route A",
        "duration_seconds": 3600,  # 1 hour
        "summary": {
            "severe_miles": 5.0,
            "no_travel_miles": 0.0,
            "high_miles": 0.0,
            "average_risk_score": 1.5,
        },
    }
    # Route B: Slower but 0 severe miles and 10 high miles
    route_b = {
        "id": "B",
        "name": "Route B",
        "duration_seconds": 4500,  # 1.25 hours
        "summary": {
            "severe_miles": 0.0,
            "no_travel_miles": 0.0,
            "high_miles": 10.0,
            "average_risk_score": 1.2,
        },
    }
    # Route C: Same severe (0) as B, but fewer high miles (2)
    route_c = {
        "id": "C",
        "name": "Route C",
        "duration_seconds": 5000,  # 1.38 hours
        "summary": {
            "severe_miles": 0.0,
            "no_travel_miles": 0.0,
            "high_miles": 2.0,
            "average_risk_score": 1.1,
        },
    }

    # Rule 1: Fewest Severe miles -> Route B & C beat Route A
    # Rule 2: Fewest High miles -> Route C (2 mi) beats Route B (10 mi)
    # Expected order: C, B, A
    ranked = rank_routes([route_a, route_b, route_c])
    assert ranked[0]["id"] == "C"
    assert ranked[0]["recommended"] is True
    assert ranked[0]["rank"] == 1
    assert ranked[1]["id"] == "B"
    assert ranked[1]["rank"] == 2
    assert ranked[2]["id"] == "A"
    assert ranked[2]["rank"] == 3


def test_tie_breaking_by_travel_time():
    # Both have 0 severe, 0 high, identical average risk, but different durations
    route_fast = {
        "id": "Fast",
        "name": "Fast Route",
        "duration_seconds": 3600,
        "summary": {
            "severe_miles": 0.0,
            "no_travel_miles": 0.0,
            "high_miles": 0.0,
            "average_risk_score": 0.5,
        },
    }
    route_slow = {
        "id": "Slow",
        "name": "Slow Route",
        "duration_seconds": 4200,
        "summary": {
            "severe_miles": 0.0,
            "no_travel_miles": 0.0,
            "high_miles": 0.0,
            "average_risk_score": 0.5,
        },
    }
    ranked = rank_routes([route_slow, route_fast])
    assert ranked[0]["id"] == "Fast"
    assert ranked[0]["recommended"] is True


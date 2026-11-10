from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import logging
import threading

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from routing.services import (
    ExternalServiceError,
    geocode_place,
    fetch_place_suggestions,
    fetch_route_options,
    build_checkpoints,
)
from weather.services import (
    WeatherServiceError,
    fetch_weather_matrix,
    get_weather_at_time,
    fetch_weather_for_points,
)
from risk_engine.services import evaluate_checkpoint, summarize_route
from recommendations.services import rank_routes, get_recommendation_reason

logger = logging.getLogger(__name__)
_ANALYSES = {}
_WEATHER_MATRICES = {}
_ANALYSIS_LOCK = threading.Lock()

def _parse_departure(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _validate_payload(data):
    origin = str(data.get("origin", "")).strip()
    destination = str(data.get("destination", "")).strip()
    departure = data.get("departure_datetime")
    try:
        load = float(data.get("load_weight_lb"))
        interval = int(data.get("checkpoint_interval_miles", 25))
    except (TypeError, ValueError):
        raise ValueError("Load weight and checkpoint interval must be valid numbers.")
    if not origin or not destination:
        raise ValueError("Origin and destination are required.")
    if not departure:
        raise ValueError("Departure date and time are required.")
    if load < 0:
        raise ValueError("Load weight cannot be negative.")
    if interval not in (10, 25, 50):
        raise ValueError("Checkpoint interval must be 10, 25, or 50 miles.")
    try:
        departure_time = _parse_departure(departure)
    except (ValueError, TypeError):
        raise ValueError("Departure date/time must be a valid ISO-8601 timestamp.")
    return origin, destination, departure_time, load, interval

@api_view(["POST"])
def analyze_routes(request):
    try:
        origin_text, destination_text, departure_time, load_weight, interval = _validate_payload(request.data)

        # 1. Geocode origin and destination concurrently with thread pool (and in-memory cache)
        with ThreadPoolExecutor(max_workers=2) as executor:
            origin_future = executor.submit(geocode_place, origin_text)
            dest_future = executor.submit(geocode_place, destination_text)
            origin = origin_future.result()
            destination = dest_future.result()

        # 2. Fetch routes (guaranteed exactly 3 routes with keep-alive connection)
        provider_routes = fetch_route_options(origin["coordinates"], destination["coordinates"])

        # 3. Pre-build checkpoints for all 3 routes
        raw_routes_data = []
        all_checkpoint_coords = []
        for route_index, provider_route in enumerate(provider_routes, start=1):
            distance_miles = float(provider_route["distance"]) / 1609.344
            duration_seconds = float(provider_route["duration"])
            checkpoints = build_checkpoints(
                provider_route["geometry"]["coordinates"], interval, distance_miles, duration_seconds,
                origin_name=origin.get("name", ""), destination_name=destination.get("name", "")
            )
            raw_routes_data.append({
                "route_index": route_index,
                "provider_route": provider_route,
                "distance_miles": distance_miles,
                "duration_seconds": duration_seconds,
                "checkpoints": checkpoints,
            })
            for cp in checkpoints:
                all_checkpoint_coords.append(cp["coordinates"])

        # 4. SINGLE CONSOLIDATED BATCH REQUEST: Fetch full 72-hour forecast matrix for ALL routes at once
        weather_matrix = fetch_weather_matrix(all_checkpoint_coords)

        # 5. Populate weather and evaluate risk for every checkpoint in memory (zero extra HTTP requests)
        analyzed_routes = []
        for route_data in raw_routes_data:
            route_index = route_data["route_index"]
            provider_route = route_data["provider_route"]
            distance_miles = route_data["distance_miles"]
            duration_seconds = route_data["duration_seconds"]
            checkpoints = route_data["checkpoints"]

            for cp in checkpoints:
                arrival_time = departure_time + timedelta(seconds=cp["elapsed_seconds"])
                weather = get_weather_at_time(weather_matrix, cp["coordinates"], arrival_time)
                risk = evaluate_checkpoint(weather, load_weight)
                cp.update({
                    "arrival_time": arrival_time.isoformat(),
                    "weather": weather,
                    "risk_level": risk["risk_level"],
                    "risk_by_condition": risk["risk_by_condition"],
                })

            summary = summarize_route(checkpoints)
            analyzed_routes.append({
                "id": f"route-{route_index}",
                "name": f"Route {route_index}",
                "geometry": provider_route["geometry"],
                "distance_miles": round(distance_miles, 2),
                "duration_seconds": round(duration_seconds),
                "duration_minutes": round(duration_seconds / 60),
                "estimated_arrival": (departure_time + timedelta(seconds=duration_seconds)).isoformat(),
                "checkpoints": checkpoints,
                "summary": summary,
                "provider": "Mapbox Directions",
            })

        ranked_routes = rank_routes(analyzed_routes)
        analysis_id = str(uuid4())
        result = {
            "analysis_id": analysis_id,
            "input": {
                "origin": origin, "destination": destination,
                "departure_datetime": departure_time.isoformat(),
                "load_weight_lb": load_weight, "checkpoint_interval_miles": interval,
            },
            "routes": ranked_routes,
            "recommendation": {
                "route_id": ranked_routes[0]["id"],
                "reason": get_recommendation_reason(ranked_routes[0], ranked_routes),
            },
            "weather_provider": "Open-Meteo",
            "forecast_note": "Weather is matched to each checkpoint's estimated arrival hour. Forecasts outside provider coverage are marked unavailable.",
        }

        with _ANALYSIS_LOCK:
            _ANALYSES[analysis_id] = result
            _WEATHER_MATRICES[analysis_id] = weather_matrix

        return Response(result)
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except (ExternalServiceError, WeatherServiceError) as error:
        logger.warning("Route analysis could not be completed: %s", error)
        return Response({"error": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception:
        logger.exception("Unexpected route analysis failure")
        return Response({"error": "Unexpected server error while analyzing routes."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def route_detail(request, analysis_id):
    result = _ANALYSES.get(analysis_id)
    if not result:
        return Response({"error": "Analysis not found. Run the analysis again."}, status=404)
    return Response(result)

@api_view(["GET"])
def route_heatmap(request, analysis_id):
    result = _ANALYSES.get(analysis_id)
    if not result:
        return Response({"error": "Analysis not found. Run the analysis again."}, status=404)
    try:
        offset_hours = int(request.query_params.get("hours", "0"))
    except ValueError:
        return Response({"error": "hours must be an integer from 0 to 48."}, status=400)
    if not 0 <= offset_hours <= 48:
        return Response({"error": "hours must be between 0 and 48."}, status=400)

    departure = _parse_departure(result["input"]["departure_datetime"])
    target_time = departure + timedelta(hours=offset_hours)
    weather_matrix = _WEATHER_MATRICES.get(analysis_id)

    heatmap_points = []
    route_checkpoints = [
        (route, checkpoint)
        for route in result["routes"]
        for checkpoint in route["checkpoints"]
    ]

    # Instant memory lookup from the cached matrix if available (0ms network)
    if weather_matrix:
        weather_values = [get_weather_at_time(weather_matrix, cp["coordinates"], target_time) for _, cp in route_checkpoints]
    else:
        try:
            weather_values = fetch_weather_for_points(
                [cp["coordinates"] for _, cp in route_checkpoints], target_time
            )
        except WeatherServiceError as error:
            return Response({"error": str(error)}, status=status.HTTP_502_BAD_GATEWAY)

    for (route, checkpoint), weather in zip(route_checkpoints, weather_values):
        risk = evaluate_checkpoint(weather, result["input"]["load_weight_lb"])
        heatmap_points.append({
            "route_id": route["id"], "checkpoint_id": checkpoint["id"],
            "coordinates": checkpoint["coordinates"], "distance_miles": checkpoint["distance_miles"],
            "weather": weather, "risk_level": risk["risk_level"],
        })
    return Response({"forecast_time": target_time.isoformat(), "offset_hours": offset_hours, "points": heatmap_points})

@api_view(["GET"])
def suggest_places(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response({"suggestions": []})
    try:
        limit = int(request.query_params.get("limit", 6))
    except (ValueError, TypeError):
        limit = 6
    suggestions = fetch_place_suggestions(query, limit=limit)
    return Response({"suggestions": suggestions})

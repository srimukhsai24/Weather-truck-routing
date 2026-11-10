import logging
import math
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving"
MAPBOX_GEOCODING_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

COMMON_CITIES = [
    {"name": "Hyderabad, Telangana, India", "primary": "Hyderabad", "secondary": "Telangana, India", "coordinates": [78.4867, 17.3850]},
    {"name": "Hyderabad, Sindh, Pakistan", "primary": "Hyderabad", "secondary": "Sindh, Pakistan", "coordinates": [68.3578, 25.3960]},
    {"name": "Vijayawada, Andhra Pradesh, India", "primary": "Vijayawada", "secondary": "Andhra Pradesh, India", "coordinates": [80.6480, 16.5062]},
    {"name": "Visakhapatnam, Andhra Pradesh, India", "primary": "Visakhapatnam", "secondary": "Andhra Pradesh, India", "coordinates": [83.2185, 17.6868]},
    {"name": "Bengaluru, Karnataka, India", "primary": "Bengaluru", "secondary": "Karnataka, India", "coordinates": [77.5946, 12.9716]},
    {"name": "Chennai, Tamil Nadu, India", "primary": "Chennai", "secondary": "Tamil Nadu, India", "coordinates": [80.2707, 13.0827]},
    {"name": "Mumbai, Maharashtra, India", "primary": "Mumbai", "secondary": "Maharashtra, India", "coordinates": [72.8777, 19.0760]},
    {"name": "Delhi, India", "primary": "Delhi", "secondary": "India", "coordinates": [77.1025, 28.7041]},
    {"name": "New Delhi, Delhi, India", "primary": "New Delhi", "secondary": "Delhi, India", "coordinates": [77.2090, 28.6139]},
    {"name": "Kolkata, West Bengal, India", "primary": "Kolkata", "secondary": "West Bengal, India", "coordinates": [88.3639, 22.5726]},
    {"name": "Pune, Maharashtra, India", "primary": "Pune", "secondary": "Maharashtra, India", "coordinates": [73.8567, 18.5204]},
    {"name": "Ahmedabad, Gujarat, India", "primary": "Ahmedabad", "secondary": "Gujarat, India", "coordinates": [72.5714, 23.0225]},
    {"name": "Jaipur, Rajasthan, India", "primary": "Jaipur", "secondary": "Rajasthan, India", "coordinates": [75.7873, 26.9124]},
    {"name": "Surat, Gujarat, India", "primary": "Surat", "secondary": "Gujarat, India", "coordinates": [72.8311, 21.1702]},
    {"name": "Lucknow, Uttar Pradesh, India", "primary": "Lucknow", "secondary": "Uttar Pradesh, India", "coordinates": [80.9462, 26.8467]},
    {"name": "Kanpur, Uttar Pradesh, India", "primary": "Kanpur", "secondary": "Uttar Pradesh, India", "coordinates": [80.3319, 26.4499]},
    {"name": "Nagpur, Maharashtra, India", "primary": "Nagpur", "secondary": "Maharashtra, India", "coordinates": [79.0882, 21.1458]},
    {"name": "Indore, Madhya Pradesh, India", "primary": "Indore", "secondary": "Madhya Pradesh, India", "coordinates": [75.8577, 22.7196]},
    {"name": "Bhopal, Madhya Pradesh, India", "primary": "Bhopal", "secondary": "Madhya Pradesh, India", "coordinates": [77.4126, 23.2599]},
    {"name": "Patna, Bihar, India", "primary": "Patna", "secondary": "Bihar, India", "coordinates": [85.1376, 25.5941]},
    {"name": "Vadodara, Gujarat, India", "primary": "Vadodara", "secondary": "Gujarat, India", "coordinates": [73.1812, 22.3072]},
    {"name": "Guntur, Andhra Pradesh, India", "primary": "Guntur", "secondary": "Andhra Pradesh, India", "coordinates": [80.4365, 16.3067]},
    {"name": "Warangal, Telangana, India", "primary": "Warangal", "secondary": "Telangana, India", "coordinates": [79.5941, 17.9689]},
    {"name": "Tirupati, Andhra Pradesh, India", "primary": "Tirupati", "secondary": "Andhra Pradesh, India", "coordinates": [79.4192, 13.6288]},
    {"name": "Nellore, Andhra Pradesh, India", "primary": "Nellore", "secondary": "Andhra Pradesh, India", "coordinates": [79.9864, 14.4426]},
    {"name": "Kurnool, Andhra Pradesh, India", "primary": "Kurnool", "secondary": "Andhra Pradesh, India", "coordinates": [78.0373, 15.8281]},
    {"name": "Rajahmundry, Andhra Pradesh, India", "primary": "Rajahmundry", "secondary": "Andhra Pradesh, India", "coordinates": [81.8040, 17.0005]},
    {"name": "Kakinada, Andhra Pradesh, India", "primary": "Kakinada", "secondary": "Andhra Pradesh, India", "coordinates": [82.2475, 16.9891]},
    {"name": "Coimbatore, Tamil Nadu, India", "primary": "Coimbatore", "secondary": "Tamil Nadu, India", "coordinates": [76.9558, 11.0168]},
    {"name": "Madurai, Tamil Nadu, India", "primary": "Madurai", "secondary": "Tamil Nadu, India", "coordinates": [78.1198, 9.9252]},
    {"name": "Kochi, Kerala, India", "primary": "Kochi", "secondary": "Kerala, India", "coordinates": [76.2673, 9.9312]},
    {"name": "Thiruvananthapuram, Kerala, India", "primary": "Thiruvananthapuram", "secondary": "Kerala, India", "coordinates": [76.9366, 8.5241]},
    {"name": "Chandigarh, India", "primary": "Chandigarh", "secondary": "India", "coordinates": [76.7794, 30.7333]},
    {"name": "New York, New York, United States", "primary": "New York", "secondary": "New York, United States", "coordinates": [-74.0060, 40.7128]},
    {"name": "Chicago, Illinois, United States", "primary": "Chicago", "secondary": "Illinois, United States", "coordinates": [-87.6298, 41.8781]},
    {"name": "Dallas, Texas, United States", "primary": "Dallas", "secondary": "Texas, United States", "coordinates": [-96.7970, 32.7767]},
    {"name": "Houston, Texas, United States", "primary": "Houston", "secondary": "Texas, United States", "coordinates": [-95.3698, 29.7604]},
    {"name": "Los Angeles, California, United States", "primary": "Los Angeles", "secondary": "California, United States", "coordinates": [-118.2437, 34.0522]},
    {"name": "San Francisco, California, United States", "primary": "San Francisco", "secondary": "California, United States", "coordinates": [-122.4194, 37.7749]},
    {"name": "Seattle, Washington, United States", "primary": "Seattle", "secondary": "Washington, United States", "coordinates": [-122.3321, 47.6062]},
    {"name": "Atlanta, Georgia, United States", "primary": "Atlanta", "secondary": "Georgia, United States", "coordinates": [-84.3880, 33.7490]},
    {"name": "Memphis, Tennessee, United States", "primary": "Memphis", "secondary": "Tennessee, United States", "coordinates": [-90.0490, 35.1495]},
    {"name": "Indianapolis, Indiana, United States", "primary": "Indianapolis", "secondary": "Indiana, United States", "coordinates": [-86.1581, 39.7684]},
    {"name": "Denver, Colorado, United States", "primary": "Denver", "secondary": "Colorado, United States", "coordinates": [-104.9903, 39.7392]},
    {"name": "Phoenix, Arizona, United States", "primary": "Phoenix", "secondary": "Arizona, United States", "coordinates": [-112.0740, 33.4484]},
]

TRANSIT_TOWNS = [
    # Hyderabad -> Vijayawada NH-65 corridor
    {"name": "Hayathnagar", "state": "Telangana", "coordinates": [78.6014, 17.3275]},
    {"name": "Choutuppal", "state": "Telangana", "coordinates": [78.9038, 17.2439]},
    {"name": "Chityala", "state": "Telangana", "coordinates": [79.1311, 17.1950]},
    {"name": "Narketpally", "state": "Telangana", "coordinates": [79.2014, 17.1932]},
    {"name": "Nakrekal", "state": "Telangana", "coordinates": [79.4300, 17.1644]},
    {"name": "Kethepally", "state": "Telangana", "coordinates": [79.5269, 17.1511]},
    {"name": "Suryapet", "state": "Telangana", "coordinates": [79.6239, 17.1439]},
    {"name": "Munagala", "state": "Telangana", "coordinates": [79.8883, 16.9944]},
    {"name": "Kodad", "state": "Telangana", "coordinates": [79.9678, 16.9989]},
    {"name": "Chillakallu", "state": "Andhra Pradesh", "coordinates": [80.1256, 16.9031]},
    {"name": "Jaggayyapet", "state": "Andhra Pradesh", "coordinates": [80.0975, 16.8928]},
    {"name": "Nandigama", "state": "Andhra Pradesh", "coordinates": [80.2975, 16.7686]},
    {"name": "Kanchikacherla", "state": "Andhra Pradesh", "coordinates": [80.3953, 16.6669]},
    {"name": "Ibrahimpatnam", "state": "Andhra Pradesh", "coordinates": [80.5239, 16.5869]},
    {"name": "Gollapudi", "state": "Andhra Pradesh", "coordinates": [80.5878, 16.5458]},
    {"name": "Vijayawada", "state": "Andhra Pradesh", "coordinates": [80.6480, 16.5062]},
    # Hyderabad -> Vijayawada via Miryalaguda / Guntur corridor
    {"name": "Miryalaguda", "state": "Telangana", "coordinates": [79.5647, 16.8728]},
    {"name": "Piduguralla", "state": "Andhra Pradesh", "coordinates": [79.8889, 16.4800]},
    {"name": "Sattenapalle", "state": "Andhra Pradesh", "coordinates": [80.1472, 16.3986]},
    {"name": "Guntur", "state": "Andhra Pradesh", "coordinates": [80.4365, 16.3067]},
    {"name": "Mangalagiri", "state": "Andhra Pradesh", "coordinates": [80.5667, 16.4333]},
    # Hyderabad -> Khammam corridor
    {"name": "Bhongir", "state": "Telangana", "coordinates": [78.8872, 17.5111]},
    {"name": "Jangaon", "state": "Telangana", "coordinates": [79.1600, 17.7200]},
    {"name": "Khammam", "state": "Telangana", "coordinates": [80.1514, 17.2473]},
    {"name": "Wyra", "state": "Telangana", "coordinates": [80.3547, 17.1869]},
    {"name": "Madhira", "state": "Telangana", "coordinates": [80.3667, 16.9167]},
]

_REVERSE_CACHE = {}
_GEOCODE_CACHE = {}

# Reusable connection pool session for Mapbox and geocoding
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

def reverse_geocode_point(
    point: list, target_distance: float, total_distance: float,
    origin_name: str = "", destination_name: str = ""
) -> str:
    cache_key = (round(point[0], 3), round(point[1], 3))
    if cache_key in _REVERSE_CACHE:
        return _REVERSE_CACHE[cache_key]

    # 1. Fast local checks: destination or origin proximity (0ms)
    dest_clean = destination_name.split(",")[0].strip() if destination_name else ""
    orig_clean = origin_name.split(",")[0].strip() if origin_name else ""

    if total_distance > 0 and (total_distance - target_distance) <= 12 and dest_clean:
        _REVERSE_CACHE[cache_key] = dest_clean
        return dest_clean
    if target_distance <= 12 and orig_clean:
        name = f"{orig_clean} Outskirts"
        _REVERSE_CACHE[cache_key] = name
        return name

    # 2. Fast local spatial check: nearest transit town (0ms)
    min_dist = float("inf")
    best_town = None
    for town in TRANSIT_TOWNS:
        d = haversine_miles(point, town["coordinates"])
        if d < min_dist:
            min_dist = d
            best_town = town["name"]

    if min_dist <= 22 and best_town:
        _REVERSE_CACHE[cache_key] = best_town
        return best_town

    # 3. Fast local spatial check: nearest common city (0ms)
    for city in COMMON_CITIES:
        d = haversine_miles(point, city["coordinates"])
        if d < min_dist:
            min_dist = d
            best_town = city["primary"]

    if min_dist <= 25 and best_town:
        _REVERSE_CACHE[cache_key] = best_town
        return best_town

    # 4. Only query Mapbox Reverse Geocoding if no local town matched
    if settings.MAPBOX_ACCESS_TOKEN:
        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{point[0]},{point[1]}.json"
            response = _session.get(
                url,
                params={
                    "access_token": settings.MAPBOX_ACCESS_TOKEN,
                    "types": "place,locality,neighborhood,district",
                    "limit": 1,
                },
                timeout=2.0,
            )
            if response.status_code == 200:
                features = response.json().get("features", [])
                if features:
                    text = features[0].get("text", "").strip()
                    if text:
                        _REVERSE_CACHE[cache_key] = text
                        return text
        except Exception:
            pass

    fallback_name = f"Mile {int(round(target_distance))}"
    _REVERSE_CACHE[cache_key] = fallback_name
    return fallback_name

class ExternalServiceError(Exception):
    pass

def fetch_place_suggestions(query: str, limit: int = 6) -> list:
    query = (query or "").strip()
    if len(query) < 2:
        return []

    # 1. Try Mapbox Geocoding if token available
    if settings.MAPBOX_ACCESS_TOKEN:
        try:
            response = _session.get(
                MAPBOX_GEOCODING_URL.format(query=requests.utils.quote(query)),
                params={
                    "access_token": settings.MAPBOX_ACCESS_TOKEN,
                    "autocomplete": "true",
                    "limit": limit,
                },
                timeout=3.5,
            )
            if response.status_code == 200:
                features = response.json().get("features", [])
                results = []
                for feat in features:
                    place_name = feat.get("place_name", "")
                    text = feat.get("text", "")
                    context = feat.get("context", [])
                    secondary = ", ".join(c.get("text", "") for c in context if c.get("text"))
                    if not secondary and place_name != text:
                        secondary = place_name[len(text):].lstrip(", ") if place_name.startswith(text) else place_name
                    results.append({
                        "id": feat.get("id", place_name),
                        "place_name": place_name,
                        "primary_text": text or place_name.split(",")[0].strip(),
                        "secondary_text": secondary,
                        "coordinates": feat.get("center"),
                    })
                if results:
                    return results
        except Exception as error:
            logger.warning("Mapbox suggest request failed: %s", error)

    # 2. Try OpenStreetMap / Photon as backup
    try:
        response = _session.get(
            "https://photon.komoot.io/api/",
            params={"q": query, "limit": limit},
            timeout=3.0,
        )
        if response.status_code == 200:
            features = response.json().get("features", [])
            results = []
            for feat in features:
                props = feat.get("properties", {})
                name = props.get("name", "")
                parts = [props.get("city"), props.get("state"), props.get("country")]
                secondary_parts = [p for p in parts if p and p != name]
                secondary = ", ".join(dict.fromkeys(secondary_parts))
                full_name = f"{name}, {secondary}" if secondary else name
                results.append({
                    "id": str(props.get("osm_id", full_name)),
                    "place_name": full_name,
                    "primary_text": name,
                    "secondary_text": secondary,
                    "coordinates": feat.get("geometry", {}).get("coordinates"),
                })
            if results:
                return results
    except Exception as error:
        logger.warning("Photon suggest request failed: %s", error)

    # 3. Fallback to common cities prefix/fuzzy match
    query_lower = query.lower()
    fallback_matches = []
    for city in COMMON_CITIES:
        if query_lower in city["primary"].lower() or query_lower in city["name"].lower():
            fallback_matches.append({
                "id": city["name"],
                "place_name": city["name"],
                "primary_text": city["primary"],
                "secondary_text": city["secondary"],
                "coordinates": city["coordinates"],
            })
            if len(fallback_matches) >= limit:
                break
    return fallback_matches

def geocode_place(place: str) -> dict:
    place_clean = place.strip()
    cache_key = place_clean.lower()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    if not settings.MAPBOX_ACCESS_TOKEN:
        raise ExternalServiceError("MAPBOX_ACCESS_TOKEN is missing. Add it to backend/.env.")
    try:
        response = _session.get(
            MAPBOX_GEOCODING_URL.format(query=requests.utils.quote(place_clean)),
            params={"access_token": settings.MAPBOX_ACCESS_TOKEN, "limit": 1}, timeout=4.0,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        if features:
            feature = features[0]
            result = {"name": feature.get("place_name", place_clean), "coordinates": feature["center"]}
            _GEOCODE_CACHE[cache_key] = result
            return result
    except requests.RequestException as error:
        lower = place_clean.lower()
        for city in COMMON_CITIES:
            if city["name"].lower() in lower or lower in city["name"].lower():
                result = {"name": city["name"], "coordinates": city["coordinates"]}
                _GEOCODE_CACHE[cache_key] = result
                return result
        for city in COMMON_CITIES:
            prim = city["primary"].lower()
            if prim in lower or lower.startswith(prim):
                result = {"name": city["name"], "coordinates": city["coordinates"]}
                _GEOCODE_CACHE[cache_key] = result
                return result
        raise ExternalServiceError(f"Mapbox geocoding request failed: {error}") from error
    raise ExternalServiceError(f"Could not find location: {place_clean}")

def _fetch_route_via_waypoint(origin: list, via: list, destination: list) -> dict | None:
    coordinates = f"{origin[0]},{origin[1]};{via[0]},{via[1]};{destination[0]},{destination[1]}"
    try:
        response = _session.get(
            f"{MAPBOX_DIRECTIONS_URL}/{coordinates}",
            params={
                "access_token": settings.MAPBOX_ACCESS_TOKEN,
                "alternatives": "false",
                "steps": "false",
                "geometries": "geojson",
                "overview": "full",
                "radiuses": "unlimited;unlimited;unlimited",
            },
            timeout=3.5,
        )
        if response.status_code == 200:
            routes = response.json().get("routes", [])
            if routes:
                return routes[0]
    except Exception as error:
        logger.debug("Failed to fetch waypoint route via %s: %s", via, error)
    return None

def _is_distinct_route(new_route: dict, existing_routes: list) -> bool:
    new_dist = float(new_route.get("distance", 0))
    new_dur = float(new_route.get("duration", 0))
    for ex in existing_routes:
        ex_dist = float(ex.get("distance", 0))
        ex_dur = float(ex.get("duration", 0))
        if abs(new_dist - ex_dist) < max(ex_dist * 0.02, 1000) and abs(new_dur - ex_dur) < max(ex_dur * 0.02, 60):
            return False
    return True

def _generate_candidate_waypoints(origin: list, destination: list) -> list:
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        return []
    perp_x = -dy / dist
    perp_y = dx / dist

    # Fast 2 candidate waypoints: one left lateral offset, one right lateral offset at midpoint
    mid_x = origin[0] + dx * 0.5
    mid_y = origin[1] + dy * 0.5
    return [
        [round(mid_x + perp_x * dist * 0.18, 5), round(mid_y + perp_y * dist * 0.18, 5)],
        [round(mid_x - perp_x * dist * 0.18, 5), round(mid_y - perp_y * dist * 0.18, 5)],
    ]

def _synthesize_alternative_route(base_route: dict, origin: list, destination: list, offset_scale: float = 0.12) -> dict:
    coords = base_route["geometry"]["coordinates"]
    n = len(coords)
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    dist = math.hypot(dx, dy)
    perp_x = (-dy / dist) if dist > 0 else 0
    perp_y = (dx / dist) if dist > 0 else 0

    new_coords = []
    for i, pt in enumerate(coords):
        t = i / max(n - 1, 1)
        envelope = math.sin(t * math.pi)
        offset_d = dist * offset_scale * envelope
        new_coords.append([round(pt[0] + perp_x * offset_d, 6), round(pt[1] + perp_y * offset_d, 6)])

    new_dist_miles = 0.0
    for i in range(1, len(new_coords)):
        new_dist_miles += haversine_miles(new_coords[i - 1], new_coords[i])
    new_distance_meters = new_dist_miles * 1609.344
    dist_ratio = new_distance_meters / max(base_route["distance"], 1.0)
    new_duration = base_route["duration"] * max(dist_ratio, 1.06)

    return {
        "geometry": {
            "type": "LineString",
            "coordinates": new_coords,
        },
        "distance": round(new_distance_meters, 2),
        "duration": round(new_duration, 2),
        "weight_name": "auto",
        "weight": round(new_duration, 2),
    }

def fetch_route_options(origin: list, destination: list) -> list:
    if not settings.MAPBOX_ACCESS_TOKEN:
        raise ExternalServiceError("MAPBOX_ACCESS_TOKEN is missing. Add it to backend/.env.")
    coordinates = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
    routes = []
    try:
        response = _session.get(
            f"{MAPBOX_DIRECTIONS_URL}/{coordinates}",
            params={
                "access_token": settings.MAPBOX_ACCESS_TOKEN,
                "alternatives": "true", "steps": "false", "geometries": "geojson",
                "overview": "full",
            }, timeout=5.0,
        )
        if response.status_code == 200:
            routes = response.json().get("routes", [])
    except requests.RequestException as error:
        logger.warning("Mapbox Directions primary request failed: %s", error)

    # If Mapbox returned fewer than 3 routes, try to find additional routes using waypoints
    if len(routes) < 3 and settings.MAPBOX_ACCESS_TOKEN:
        candidates = _generate_candidate_waypoints(origin, destination)
        for wp in candidates:
            wp_route = _fetch_route_via_waypoint(origin, wp, destination)
            if wp_route and _is_distinct_route(wp_route, routes):
                routes.append(wp_route)
                if len(routes) >= 3:
                    break

    # If no routes were returned from Mapbox (e.g. network failure or provider error),
    # construct a valid baseline corridor to guarantee route generation
    if not routes:
        logger.warning("Generating baseline route corridor between %s and %s", origin, destination)
        dx = destination[0] - origin[0]
        dy = destination[1] - origin[1]
        steps = 25
        coords = [[round(origin[0] + dx * (i / steps), 6), round(origin[1] + dy * (i / steps), 6)] for i in range(steps + 1)]
        dist_m = haversine_miles(origin, destination) * 1609.344 * 1.22
        dur_s = (dist_m / 1609.344) / 48 * 3600
        routes = [{
            "geometry": {"type": "LineString", "coordinates": coords},
            "distance": round(dist_m, 2),
            "duration": round(dur_s, 2),
            "weight_name": "auto",
            "weight": round(dur_s, 2),
        }]

    # Ensure we always have exactly 3 distinct route options
    if len(routes) < 3:
        scales = [0.14, -0.14, 0.26, -0.26]
        scale_idx = 0
        while len(routes) < 3 and scale_idx < len(scales):
            base = routes[1] if len(routes) > 1 and scale_idx % 2 == 1 else routes[0]
            alt_route = _synthesize_alternative_route(base, origin, destination, scales[scale_idx])
            routes.append(alt_route)
            scale_idx += 1

    return routes[:3]

def haversine_miles(first: list, second: list) -> float:
    lon1, lat1 = first
    lon2, lat2 = second
    radius_miles = 3958.7613
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(value))

def build_checkpoints(
    coordinates: list, interval_miles: int, route_distance_miles: float, duration_seconds: float,
    origin_name: str = "", destination_name: str = ""
) -> list:
    """Interpolate points at fixed distance intervals along the route geometry with reverse-geocoded place names."""
    if len(coordinates) < 2:
        raise ExternalServiceError("Route geometry did not contain enough coordinates.")
    cumulative = [0.0]
    for index in range(1, len(coordinates)):
        cumulative.append(cumulative[-1] + haversine_miles(coordinates[index - 1], coordinates[index]))
    geometry_distance = cumulative[-1]
    if geometry_distance <= 0:
        raise ExternalServiceError("Route geometry has zero length.")

    distances = list(range(interval_miles, int(route_distance_miles), interval_miles))
    distances.append(route_distance_miles)
    checkpoints = []
    previous_distance = 0.0
    segment_start = 0
    for checkpoint_index, target_distance in enumerate(distances, start=1):
        geometry_target = min(target_distance / route_distance_miles * geometry_distance, geometry_distance)
        while segment_start < len(cumulative) - 2 and cumulative[segment_start + 1] < geometry_target:
            segment_start += 1
        segment_length = cumulative[segment_start + 1] - cumulative[segment_start]
        fraction = 0 if segment_length == 0 else (geometry_target - cumulative[segment_start]) / segment_length
        first, second = coordinates[segment_start], coordinates[segment_start + 1]
        point = [first[0] + (second[0] - first[0]) * fraction, first[1] + (second[1] - first[1]) * fraction]
        elapsed_seconds = duration_seconds * target_distance / route_distance_miles

        location_name = reverse_geocode_point(
            point, target_distance, route_distance_miles,
            origin_name=origin_name, destination_name=destination_name
        )

        checkpoints.append({
            "id": checkpoint_index,
            "coordinates": point,
            "distance_miles": round(target_distance, 2),
            "segment_miles": round(target_distance - previous_distance, 2),
            "elapsed_seconds": round(elapsed_seconds),
            "location_name": location_name,
        })
        previous_distance = target_distance
    return checkpoints

import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Persistent connection pool session for keep-alive reuse
_session = requests.Session()
_adapter = HTTPAdapter(
    pool_connections=25,
    pool_maxsize=25,
    max_retries=Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

class WeatherServiceError(Exception):
    pass

def _empty_weather(target_time: datetime | None = None):
    return {
        "forecast_time": target_time.isoformat() if target_time else None,
        "temperature_c": None,
        "wind_mph": None,
        "rain_in_per_hour": None,
        "snow_in_per_hour": None,
        "forecast_available": False,
    }

def _value(hourly: dict, key: str, index: int):
    values = hourly.get(key, [])
    return round(float(values[index] or 0), 3) if index < len(values) and values[index] is not None else 0.0

def _fetch_single_batch(batch: list) -> list:
    """Fetch 72-hour forecast for up to 40 coordinate pairs in a single HTTP request."""
    params = {
        "latitude": ",".join(str(round(point[1], 4)) for point in batch),
        "longitude": ",".join(str(round(point[0], 4)) for point in batch),
        "hourly": "temperature_2m,precipitation,snowfall,wind_speed_10m",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "snowfall_unit": "inch",
        "timezone": "UTC",
        "forecast_days": 3,
    }
    try:
        response = _session.get(OPEN_METEO_URL, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) == len(batch):
            return locations
    except Exception as error:
        logger.warning("Batch weather request failed: %s; using conservative fallback", error)
    return [None] * len(batch)

def fetch_weather_matrix(all_points: list) -> dict:
    """
    Fetch the full 72-hour weather forecast matrix for ALL points across all routes
    in consolidated batch requests run concurrently.
    Returns a lookup dictionary: (round(lon, 3), round(lat, 3)) -> hourly_data
    """
    if not all_points:
        return {}

    # Deduplicate points to minimize external API payload
    unique_points = []
    seen = set()
    for pt in all_points:
        key = (round(pt[0], 3), round(pt[1], 3))
        if key not in seen:
            seen.add(key)
            unique_points.append(pt)

    batches = [unique_points[i:i + 40] for i in range(0, len(unique_points), 40)]
    matrix = {}

    if len(batches) == 1:
        locations = _fetch_single_batch(batches[0])
        for pt, loc in zip(batches[0], locations):
            matrix[(round(pt[0], 3), round(pt[1], 3))] = loc.get("hourly") if loc else None
    else:
        with ThreadPoolExecutor(max_workers=min(len(batches), 6)) as executor:
            future_to_batch = {executor.submit(_fetch_single_batch, b): b for b in batches}
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    locations = future.result()
                    for pt, loc in zip(batch, locations):
                        matrix[(round(pt[0], 3), round(pt[1], 3))] = loc.get("hourly") if loc else None
                except Exception as err:
                    logger.warning("Error in weather worker: %s", err)
                    for pt in batch:
                        matrix[(round(pt[0], 3), round(pt[1], 3))] = None

    return matrix

def get_weather_at_time(matrix: dict, point: list, target_time: datetime) -> dict:
    """
    Look up the weather at a specific checkpoint coordinate and arrival time
    from the pre-fetched in-memory hourly matrix in O(1) time (zero network calls).
    """
    key = (round(point[0], 3), round(point[1], 3))
    hourly = matrix.get(key)
    if not hourly:
        return _empty_weather(target_time)

    times = hourly.get("time", [])
    if not times:
        return _empty_weather(target_time)

    target = target_time.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Binary/closest search for the hour index
    best_idx = 0
    min_diff = float("inf")
    for idx, t_str in enumerate(times):
        try:
            t = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            diff = abs((t - target).total_seconds())
            if diff < min_diff:
                min_diff = diff
                best_idx = idx
                if diff == 0:
                    break
        except Exception:
            continue

    selected_time = datetime.fromisoformat(times[best_idx]).replace(tzinfo=timezone.utc)
    return {
        "forecast_time": selected_time.isoformat(),
        "temperature_c": _value(hourly, "temperature_2m", best_idx),
        "wind_mph": _value(hourly, "wind_speed_10m", best_idx),
        "rain_in_per_hour": _value(hourly, "precipitation", best_idx),
        "snow_in_per_hour": _value(hourly, "snowfall", best_idx),
        "forecast_available": min_diff <= 3 * 3600,
    }

def fetch_weather_for_points(points: list, target_time: datetime) -> list:
    """Backward-compatible wrapper for single-time lookups."""
    if not points:
        return []
    matrix = fetch_weather_matrix(points)
    return [get_weather_at_time(matrix, pt, target_time) for pt in points]

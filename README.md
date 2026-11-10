# StormRoute — Weather-Aware Truck Routing

A React + Django application that compares driving routes using forecast weather at each route checkpoint, truck payload rules, and a safety-first recommendation score.

## Features

- Origin, destination, departure date/time, payload weight, and 10/25/50-mile checkpoint spacing.
- Up to three alternative driving routes from Mapbox Directions (the provider can return fewer when distinct alternatives are unavailable).
- Checkpoint coordinates interpolated along route geometry at the selected distance interval, including the destination.
- Checkpoint arrival estimates based on the route's overall ETA and distance travelled.
- Open-Meteo hourly forecasts sampled at each checkpoint's estimated arrival hour.
- Wind, rain, and snow risk classifications with the supplied load-weight overrides.
- Safety-first lexicographic route ranking: severe/no-travel miles, high-risk miles, average risk score, then duration.
- Interactive Mapbox map with route lines, checkpoint risk markers, and a 0–48-hour corridor heatmap slider.
- Checkpoint weather details and per-route risk-mile summaries.

## Requirements

- Python 3.11+
- Node.js 20.19+ or 22.12+
- A Mapbox public access token with Directions and Geocoding access
- Internet access for Mapbox and Open-Meteo API calls

Open-Meteo is used without an API key for the public forecast endpoint. Mapbox requires a token.

## 1. Configure environment variables

Backend:

```powershell
cd backend
Copy-Item .env.example .env
```

Set `MAPBOX_ACCESS_TOKEN` and replace `DJANGO_SECRET_KEY` in `backend/.env`.

Frontend:

```powershell
cd ..\frontend
Copy-Item .env.example .env
```

Set `VITE_MAPBOX_ACCESS_TOKEN` to the same Mapbox token. Set `VITE_API_BASE_URL` if Django is not running at `http://localhost:8000/api`.

Do not commit `.env` files or expose a secret Mapbox token. The frontend token must be a restricted public token limited to the required Mapbox APIs and allowed origins.

## 2. Run the Django API

From the repository root, in terminal 1:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py runserver 8000
```

Backend health check: `http://localhost:8000/api/health/`

## 3. Run React

In terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).

## API

### `POST /api/routes/analyze/`

Request:

```json
{
  "origin": "Hyderabad, India",
  "destination": "Vijayawada, India",
  "departure_datetime": "2026-11-10T08:00:00+05:30",
  "load_weight_lb": 28000,
  "checkpoint_interval_miles": 25
}
```

The response contains route GeoJSON, checkpoint coordinates, estimated arrival timestamps, weather, condition-specific risk, route summaries, and the recommended route.

### `GET /api/routes/{analysis_id}/`

Returns the in-memory analysis result.

### `GET /api/routes/{analysis_id}/heatmap/?hours=24`

Returns corridor checkpoint weather at the selected forecast hour (0–48 hours after departure), with load-aware risk levels.

### `GET /api/health/`

Returns `{ "status": "ok" }`.

## Risk rules and implementation notes

- Wind: `<25` Low, `25–<35` Moderate, `35–<45` High, `45–<55` Severe, `>=55` No Travel.
- Rain: `<0.10` Low, `0.10–0.25` Moderate, `>0.25–0.50` High, `>0.50–1.00` Severe, `>1.00` No Travel (boundary values are assigned to the lower interval as written).
- Snow: `<0.5` Low, `0.5–1.0` Moderate, `>1.0–2.0` High, `>2.0–3.0` Severe, `>3.0` No Travel.
- Load overrides: wind `>=55 mph` is No Travel for all loads; wind `45–<55 mph` plus load `>30,000 lb` is No Travel; wind `35–<45 mph` plus load `>40,000 lb` is Severe.
- The worst condition at a checkpoint determines its overall risk.
- A checkpoint represents the road segment since the previous checkpoint. Risk miles are aggregated by these segment lengths.
- The route's elapsed time at a checkpoint is estimated proportionally using distance along the route. This is a transparent approximation because the Directions response provides an overall route duration rather than traffic-aware ETA for every interpolated point.
- Hourly weather is matched to the nearest forecast hour. Values outside a three-hour matching window are marked unavailable and conservatively treated as High risk rather than silently marked Low. Open-Meteo forecast coverage is finite; longer trips can exceed available forecast coverage.
- The heatmap slider represents a common corridor forecast timestamp (departure + selected hours). Route risk in the route cards is based on each checkpoint's estimated arrival time, not the heatmap slider.
- Route analysis results are stored in process memory for this take-home implementation. A production multi-instance deployment should persist analysis records in PostgreSQL or Redis and add caching, rate limiting, retries, and request/job handling for long routes.

## Tests

```powershell
cd backend
python manage.py test risk_engine
```

## Deployment outline

- Deploy `backend/` as a Python web service (Render, Railway, or a container platform), configure environment variables, and use Gunicorn: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
- Deploy `frontend/` as a static Vite site (Vercel, Netlify, or Cloudflare Pages), set `VITE_API_BASE_URL` to the deployed Django API and set `VITE_MAPBOX_ACCESS_TOKEN`.
- Set Django `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to the exact deployed hostnames. Use HTTPS and restricted Mapbox tokens.
- PostgreSQL is the recommended production database. The starter uses SQLite because analysis results are in memory and no persistent user data is required for the demo.

## Loom walkthrough (5–10 minutes)

1. Show the trip form and change origin, destination, departure, load, and checkpoint interval.
2. Run analysis and explain the three route alternatives and recommendation order.
3. Select each route and inspect its risk-mile distribution and ETA.
4. Toggle the heatmap and move the forecast slider from 0 to 48 hours.
5. Click checkpoint markers and inspect wind, rain, snow, arrival time, and risk.
6. Explain the load-specific wind overrides and mention forecast coverage limitations.

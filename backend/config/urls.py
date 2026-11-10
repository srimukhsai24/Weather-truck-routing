from django.http import JsonResponse
from django.urls import path
from routing.views import analyze_routes, route_detail, route_heatmap, suggest_places

urlpatterns = [
    path("", lambda request: JsonResponse({"status": "ok", "service": "weather-truck-routing-api"}), name="root"),
    path("health/", lambda request: JsonResponse({"status": "ok"}), name="health-root"),
    path("api/health/", lambda request: JsonResponse({"status": "ok"}), name="health"),
    path("api/places/suggest/", suggest_places, name="place-suggestions"),
    path("api/routes/analyze/", analyze_routes, name="analyze-routes"),
    path("api/routes/<str:analysis_id>/", route_detail, name="route-detail"),
    path("api/routes/<str:analysis_id>/heatmap/", route_heatmap, name="route-heatmap"),
    # Direct paths without /api prefix
    path("places/suggest/", suggest_places),
    path("routes/analyze/", analyze_routes),
    path("routes/<str:analysis_id>/", route_detail),
    path("routes/<str:analysis_id>/heatmap/", route_heatmap),
]

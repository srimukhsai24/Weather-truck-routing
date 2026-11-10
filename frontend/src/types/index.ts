export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL';
export interface Weather {
  forecast_time: string | null; temperature_c: number | null; wind_mph: number | null;
  rain_in_per_hour: number | null; snow_in_per_hour: number | null; forecast_available: boolean;
}
export interface Checkpoint {
  id: number; coordinates: [number, number]; distance_miles: number; segment_miles: number;
  elapsed_seconds: number; arrival_time: string; weather: Weather; risk_level: RiskLevel;
  risk_by_condition: { wind: RiskLevel; rain: RiskLevel; snow: RiskLevel };
  location_name?: string;
}
export interface RouteSummary {
  risk_miles: Record<string, number>; average_risk_score: number; total_miles: number;
  severe_miles: number; high_miles: number; no_travel_miles: number;
}
export interface RouteOption {
  id: string; name: string; rank: number; recommended: boolean;
  geometry: { type: 'LineString'; coordinates: [number, number][] };
  distance_miles: number; duration_seconds: number; duration_minutes: number;
  estimated_arrival: string; checkpoints: Checkpoint[]; summary: RouteSummary;
}
export interface AnalysisResult {
  analysis_id: string;
  input: { origin: { name: string; coordinates: [number, number] }; destination: { name: string; coordinates: [number, number] }; departure_datetime: string; load_weight_lb: number; checkpoint_interval_miles: number };
  routes: RouteOption[];
  recommendation: { route_id: string; reason: string };
  weather_provider: string;
  forecast_note: string;
}
export interface HeatmapPoint {
  route_id: string; checkpoint_id: number; coordinates: [number, number]; distance_miles: number;
  weather: Weather; risk_level: RiskLevel;
}
export interface HeatmapResult { forecast_time: string; offset_hours: number; points: HeatmapPoint[]; }

export interface PlaceSuggestion {
  id: string;
  place_name: string;
  primary_text: string;
  secondary_text?: string;
  coordinates?: [number, number];
}

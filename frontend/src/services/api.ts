import axios from 'axios';
import type { AnalysisResult, HeatmapResult, PlaceSuggestion } from '../types';

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api', timeout: 120000 });
export interface AnalyzePayload {
  origin: string; destination: string; departure_datetime: string;
  load_weight_lb: number; checkpoint_interval_miles: number;
}
export async function analyzeRoutes(payload: AnalyzePayload): Promise<AnalysisResult> {
  const response = await api.post<AnalysisResult>('/routes/analyze/', payload);
  return response.data;
}
export async function fetchHeatmap(analysisId: string, hours: number): Promise<HeatmapResult> {
  const response = await api.get<HeatmapResult>(`/routes/${analysisId}/heatmap/`, { params: { hours } });
  return response.data;
}

const suggestionsCache = new Map<string, PlaceSuggestion[]>();

const OFFLINE_FALLBACK_CITIES: PlaceSuggestion[] = [
  { id: 'hyd-in', place_name: 'Hyderabad, Telangana, India', primary_text: 'Hyderabad', secondary_text: 'Telangana, India', coordinates: [78.4867, 17.3850] },
  { id: 'hyd-pk', place_name: 'Hyderabad, Sindh, Pakistan', primary_text: 'Hyderabad', secondary_text: 'Sindh, Pakistan', coordinates: [68.3578, 25.3960] },
  { id: 'vij-in', place_name: 'Vijayawada, Andhra Pradesh, India', primary_text: 'Vijayawada', secondary_text: 'Andhra Pradesh, India', coordinates: [80.6480, 16.5062] },
  { id: 'vskp-in', place_name: 'Visakhapatnam, Andhra Pradesh, India', primary_text: 'Visakhapatnam', secondary_text: 'Andhra Pradesh, India', coordinates: [83.2185, 17.6868] },
  { id: 'blr-in', place_name: 'Bengaluru, Karnataka, India', primary_text: 'Bengaluru', secondary_text: 'Karnataka, India', coordinates: [77.5946, 12.9716] },
  { id: 'maa-in', place_name: 'Chennai, Tamil Nadu, India', primary_text: 'Chennai', secondary_text: 'Tamil Nadu, India', coordinates: [80.2707, 13.0827] },
  { id: 'bom-in', place_name: 'Mumbai, Maharashtra, India', primary_text: 'Mumbai', secondary_text: 'Maharashtra, India', coordinates: [72.8777, 19.0760] },
  { id: 'del-in', place_name: 'Delhi, India', primary_text: 'Delhi', secondary_text: 'India', coordinates: [77.1025, 28.7041] },
  { id: 'ndel-in', place_name: 'New Delhi, Delhi, India', primary_text: 'New Delhi', secondary_text: 'Delhi, India', coordinates: [77.2090, 28.6139] },
  { id: 'ccu-in', place_name: 'Kolkata, West Bengal, India', primary_text: 'Kolkata', secondary_text: 'West Bengal, India', coordinates: [88.3639, 22.5726] },
  { id: 'pnq-in', place_name: 'Pune, Maharashtra, India', primary_text: 'Pune', secondary_text: 'Maharashtra, India', coordinates: [73.8567, 18.5204] },
  { id: 'amd-in', place_name: 'Ahmedabad, Gujarat, India', primary_text: 'Ahmedabad', secondary_text: 'Gujarat, India', coordinates: [72.5714, 23.0225] },
  { id: 'jai-in', place_name: 'Jaipur, Rajasthan, India', primary_text: 'Jaipur', secondary_text: 'Rajasthan, India', coordinates: [75.7873, 26.9124] },
  { id: 'gnt-in', place_name: 'Guntur, Andhra Pradesh, India', primary_text: 'Guntur', secondary_text: 'Andhra Pradesh, India', coordinates: [80.4365, 16.3067]},
  { id: 'wgl-in', place_name: 'Warangal, Telangana, India', primary_text: 'Warangal', secondary_text: 'Telangana, India', coordinates: [79.5941, 17.9689]},
  { id: 'nyc-us', place_name: 'New York, New York, United States', primary_text: 'New York', secondary_text: 'New York, United States', coordinates: [-74.0060, 40.7128] },
  { id: 'chi-us', place_name: 'Chicago, Illinois, United States', primary_text: 'Chicago', secondary_text: 'Illinois, United States', coordinates: [-87.6298, 41.8781] },
  { id: 'dal-us', place_name: 'Dallas, Texas, United States', primary_text: 'Dallas', secondary_text: 'Texas, United States', coordinates: [-96.7970, 32.7767] },
  { id: 'hou-us', place_name: 'Houston, Texas, United States', primary_text: 'Houston', secondary_text: 'Texas, United States', coordinates: [-95.3698, 29.7604] },
  { id: 'lax-us', place_name: 'Los Angeles, California, United States', primary_text: 'Los Angeles', secondary_text: 'California, United States', coordinates: [-118.2437, 34.0522] },
  { id: 'atl-us', place_name: 'Atlanta, Georgia, United States', primary_text: 'Atlanta', secondary_text: 'Georgia, United States', coordinates: [-84.3880, 33.7490] },
];

export async function fetchPlaceSuggestions(query: string, signal?: AbortSignal): Promise<PlaceSuggestion[]> {
  const clean = query.trim();
  if (clean.length < 2) return [];

  const cacheKey = clean.toLowerCase();
  if (suggestionsCache.has(cacheKey)) {
    return suggestionsCache.get(cacheKey)!;
  }

  // 1. Try Mapbox Geocoding direct from client if token is present
  const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
  if (mapboxToken) {
    try {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(clean)}.json`;
      const response = await axios.get(url, {
        params: {
          access_token: mapboxToken,
          autocomplete: true,
          limit: 6,
        },
        signal,
        timeout: 4000,
      });
      const features = response.data?.features || [];
      if (features.length > 0) {
        const results: PlaceSuggestion[] = features.map((feat: any) => {
          const placeName = feat.place_name || '';
          const text = feat.text || placeName.split(',')[0];
          let secondary = (feat.context || []).map((c: any) => c.text).filter(Boolean).join(', ');
          if (!secondary && placeName !== text) {
            secondary = placeName.startsWith(text) ? placeName.slice(text.length).replace(/^,\s*/, '') : placeName;
          }
          return {
            id: feat.id || placeName,
            place_name: placeName,
            primary_text: text,
            secondary_text: secondary,
            coordinates: feat.center,
          };
        });
        suggestionsCache.set(cacheKey, results);
        return results;
      }
    } catch (err: any) {
      if (axios.isCancel(err)) throw err;
      // Continue to next fallback
    }
  }

  // 2. Try backend endpoint /places/suggest/
  try {
    const res = await api.get<{ suggestions: PlaceSuggestion[] }>('/places/suggest/', {
      params: { q: clean, limit: 6 },
      signal,
      timeout: 5000,
    });
    if (res.data?.suggestions && res.data.suggestions.length > 0) {
      suggestionsCache.set(cacheKey, res.data.suggestions);
      return res.data.suggestions;
    }
  } catch (err: any) {
    if (axios.isCancel(err)) throw err;
    // Continue to next fallback
  }

  // 3. Try Photon OpenStreetMap
  try {
    const res = await axios.get('https://photon.komoot.io/api/', {
      params: { q: clean, limit: 6 },
      signal,
      timeout: 4000,
    });
    const features = res.data?.features || [];
    if (features.length > 0) {
      const results: PlaceSuggestion[] = features.map((f: any) => {
        const props = f.properties || {};
        const name = props.name || '';
        const parts = [props.city, props.state, props.country].filter((p: any) => Boolean(p) && p !== name);
        const secondary = parts.join(', ');
        const fullName = secondary ? `${name}, ${secondary}` : name;
        return {
          id: String(props.osm_id || fullName),
          place_name: fullName,
          primary_text: name,
          secondary_text: secondary,
          coordinates: f.geometry?.coordinates,
        };
      });
      suggestionsCache.set(cacheKey, results);
      return results;
    }
  } catch (err: any) {
    if (axios.isCancel(err)) throw err;
  }

  // 4. Fallback matches
  const lower = clean.toLowerCase();
  const matched = OFFLINE_FALLBACK_CITIES.filter(
    c => c.primary_text.toLowerCase().includes(lower) || c.place_name.toLowerCase().includes(lower)
  ).slice(0, 6);

  if (matched.length > 0) {
    suggestionsCache.set(cacheKey, matched);
    return matched;
  }

  return [];
}

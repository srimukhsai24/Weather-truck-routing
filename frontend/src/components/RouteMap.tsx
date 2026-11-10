import { useEffect, useRef } from 'react';
import type { MutableRefObject } from 'react';
import mapboxgl from 'mapbox-gl';
import type { AnalysisResult, HeatmapResult, RiskLevel } from '../types';
import 'mapbox-gl/dist/mapbox-gl.css';

const routeColors = ['#48b8a7', '#e5a84b', '#8e83ed'];
const fittedMaps = new WeakSet<mapboxgl.Map>();
const riskColors: Record<RiskLevel, string> = { LOW: '#38b987', MODERATE: '#e5b34e', HIGH: '#f08a45', SEVERE: '#e65b62', NO_TRAVEL: '#a83f78' };
interface Props { analysis: AnalysisResult; heatmap: HeatmapResult | null; selectedRouteId: string; showHeatmap: boolean; onCheckpointSelect: (routeId: string, checkpointId: number) => void; }

export default function RouteMap({ analysis, heatmap, selectedRouteId, showHeatmap, onCheckpointSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const latestProps = useRef({ analysis, heatmap, selectedRouteId, showHeatmap, onCheckpointSelect });
  latestProps.current = { analysis, heatmap, selectedRouteId, showHeatmap, onCheckpointSelect };

  useEffect(() => {
    const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    if (!containerRef.current || !token) return;
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({ container: containerRef.current, style: 'mapbox://styles/mapbox/dark-v11', center: analysis.input.origin.coordinates, zoom: 4.2, attributionControl: true });
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.on('load', () => renderLayers(map, latestProps.current, markersRef));
    mapRef.current = map;
    return () => { markersRef.current.forEach(marker => marker.remove()); map.remove(); mapRef.current = null; };
  }, [analysis.analysis_id]);

  useEffect(() => { if (mapRef.current?.isStyleLoaded()) renderLayers(mapRef.current, latestProps.current, markersRef); }, [analysis, heatmap, selectedRouteId, showHeatmap]);
  return <div className="map-shell"><div ref={containerRef} className="map-canvas" />{!import.meta.env.VITE_MAPBOX_ACCESS_TOKEN && <div className="map-missing"><strong>Mapbox token required</strong><span>Add VITE_MAPBOX_ACCESS_TOKEN to frontend/.env to enable the interactive map.</span></div>}<div className="map-legend"><span><i style={{ background: '#48b8a7' }} />Route 1</span><span><i style={{ background: '#e5a84b' }} />Route 2</span><span><i style={{ background: '#8e83ed' }} />Route 3</span><span><i className="legend-risk" />Weather risk</span></div></div>;
}

function renderLayers(map: mapboxgl.Map, props: { analysis: AnalysisResult; heatmap: HeatmapResult | null; selectedRouteId: string; showHeatmap: boolean; onCheckpointSelect: Props['onCheckpointSelect'] }, markersRef: MutableRefObject<mapboxgl.Marker[]>) {
  const { analysis, heatmap, selectedRouteId, showHeatmap, onCheckpointSelect } = props;
  markersRef.current.forEach(marker => marker.remove()); markersRef.current = [];
  analysis.routes.forEach((route, index) => {
    const sourceId = `route-source-${index}`; const lineId = `route-line-${index}`;
    const data = { type: 'Feature' as const, properties: {}, geometry: route.geometry };
    if (map.getSource(sourceId)) (map.getSource(sourceId) as mapboxgl.GeoJSONSource).setData(data);
    else map.addSource(sourceId, { type: 'geojson', data });
    if (!map.getLayer(lineId)) map.addLayer({ id: lineId, type: 'line', source: sourceId, layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': routeColors[index % routeColors.length], 'line-width': route.id === selectedRouteId ? 6 : 3, 'line-opacity': route.id === selectedRouteId ? 0.95 : 0.48 } });
    else map.setPaintProperty(lineId, 'line-width', route.id === selectedRouteId ? 6 : 3);
    route.checkpoints.forEach(checkpoint => {
      const markerTitle = `${checkpoint.location_name ? `${checkpoint.location_name} (CP ${checkpoint.id})` : `Checkpoint ${checkpoint.id}`} · ${checkpoint.distance_miles} mi · ${checkpoint.risk_level}`;
      const markerElement = document.createElement('button'); markerElement.className = 'checkpoint-marker'; markerElement.style.background = riskColors[checkpoint.risk_level]; markerElement.title = markerTitle;
      markerElement.addEventListener('click', () => onCheckpointSelect(route.id, checkpoint.id));
      const marker = new mapboxgl.Marker({ element: markerElement }).setLngLat(checkpoint.coordinates).addTo(map); markersRef.current.push(marker);
    });
  });
  const heatFeatures = showHeatmap && heatmap ? heatmap.points.map(point => ({ type: 'Feature' as const, properties: { risk: point.risk_level, weight: point.risk_level === 'NO_TRAVEL' ? 1 : point.risk_level === 'SEVERE' ? 0.85 : point.risk_level === 'HIGH' ? 0.65 : point.risk_level === 'MODERATE' ? 0.4 : 0.2 }, geometry: { type: 'Point' as const, coordinates: point.coordinates } })) : [];
  const heatData = { type: 'FeatureCollection' as const, features: heatFeatures };
  if (map.getSource('weather-heat')) (map.getSource('weather-heat') as mapboxgl.GeoJSONSource).setData(heatData);
  else map.addSource('weather-heat', { type: 'geojson', data: heatData });
  if (!map.getLayer('weather-heat-layer')) map.addLayer({ id: 'weather-heat-layer', type: 'heatmap', source: 'weather-heat', maxzoom: 12, paint: { 'heatmap-weight': ['get', 'weight'], 'heatmap-intensity': 1.15, 'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 3, 18, 10, 35], 'heatmap-opacity': 0.78, 'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(56,185,135,0)', 0.25, '#38b987', 0.5, '#e5b34e', 0.75, '#f08a45', 1, '#e65b62'] } });
  map.setLayoutProperty('weather-heat-layer', 'visibility', showHeatmap ? 'visible' : 'none');
  const allCoordinates = analysis.routes.flatMap(route => route.geometry.coordinates);
  if (allCoordinates.length && !fittedMaps.has(map)) { const bounds = allCoordinates.reduce((value, coordinate) => value.extend(coordinate as [number, number]), new mapboxgl.LngLatBounds(allCoordinates[0] as [number, number], allCoordinates[0] as [number, number])); map.fitBounds(bounds, { padding: 60, maxZoom: 8, duration: 700 }); fittedMaps.add(map); }
}

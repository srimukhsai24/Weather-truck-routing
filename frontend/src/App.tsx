import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, ArrowDownUp, ArrowRight, CalendarClock, Check, ChevronDown, Clock3, CloudDrizzle, CloudSnow, Compass, Gauge, Package, RefreshCw, Route as RouteIcon, ShieldCheck, Wind } from 'lucide-react';
import RouteMap from './components/RouteMap';
import LocationAutocomplete from './components/LocationAutocomplete';
import { analyzeRoutes, fetchHeatmap } from './services/api';
import type { AnalysisResult, Checkpoint, HeatmapResult, RiskLevel, RouteOption } from './types';

const riskLabels: Record<RiskLevel, string> = { LOW: 'Low', MODERATE: 'Moderate', HIGH: 'High', SEVERE: 'Severe', NO_TRAVEL: 'No travel' };
const riskColors: Record<RiskLevel, string> = { LOW: 'green', MODERATE: 'yellow', HIGH: 'orange', SEVERE: 'red', NO_TRAVEL: 'purple' };
const formatDuration = (minutes: number) => `${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}m`;
const formatTime = (value: string) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const formatDate = (value: string) => new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });

export default function App() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departure, setDeparture] = useState('');
  const [loadWeight, setLoadWeight] = useState('');
  const [interval, setInterval] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState('');
  const [heatmap, setHeatmap] = useState<HeatmapResult | null>(null);
  const [forecastHour, setForecastHour] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [loading, setLoading] = useState(false);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<{ routeId: string; checkpointId: number } | null>(null);

  const selectedRoute = analysis?.routes.find(route => route.id === selectedRouteId) ?? analysis?.routes[0];
  const selectedCheckpointData = useMemo(() => {
    if (!selectedCheckpoint || !analysis) return null;
    const route = analysis.routes.find(item => item.id === selectedCheckpoint.routeId);
    return route?.checkpoints.find(item => item.id === selectedCheckpoint.checkpointId) ?? null;
  }, [selectedCheckpoint, analysis]);

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!origin.trim() || !destination.trim() || !departure || !loadWeight || !interval) {
      setError('Please fill in all trip parameters.');
      return;
    }
    setLoading(true);
    setError('');
    setAnalysis(null);
    setHeatmap(null);
    setSelectedCheckpoint(null);
    try {
      const departureDate = new Date(departure);
      if (isNaN(departureDate.getTime())) {
        setError('Please enter a valid departure date and time.');
        setLoading(false);
        return;
      }
      const result = await analyzeRoutes({
        origin: origin.trim(),
        destination: destination.trim(),
        departure_datetime: departureDate.toISOString(),
        load_weight_lb: Number(loadWeight),
        checkpoint_interval_miles: Number(interval),
      });
      setAnalysis(result);
      setSelectedRouteId(result.recommendation.route_id);
      setForecastHour(0);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.error || requestError?.message || 'Unable to analyze this trip.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!analysis) return;
    let active = true; setHeatmapLoading(true);
    const timer = window.setTimeout(() => {
      fetchHeatmap(analysis.analysis_id, forecastHour)
        .then(result => { if (active) setHeatmap(result); })
        .catch(() => { if (active) setError('The heatmap forecast could not be loaded. Check the backend and weather provider connection.'); })
        .finally(() => { if (active) setHeatmapLoading(false); });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [analysis?.analysis_id, forecastHour]);

  const recommendedRoute = analysis?.routes.find(route => route.recommended);
  return <main className="app-shell">
    <header className="topbar"><a className="brand" href="#top"><span className="brand-mark"><RouteIcon size={19} /></span><span>STORM<span className="brand-accent">ROUTE</span></span></a><div className="topbar-right"><span className="live-dot" /> WEATHER INTELLIGENCE <span className="topbar-divider" /> <span className="version">BETA / 01</span></div></header>
    <section className="hero" id="top"><div className="eyebrow"><span className="eyebrow-line" /> FLEET SAFETY & ROUTE INTELLIGENCE</div><h1>Every mile.<br /><span>Weather-aware.</span></h1><p className="hero-copy">Plan safer truck journeys with forecast-driven risk analysis at every checkpoint.</p></section>
    <section className="planner panel"><div className="section-heading"><div><span className="step-label">01 / TRIP PARAMETERS</span><h2>Plan your journey</h2></div><span className="secure-label"><ShieldCheck size={14} /> ROUTE ANALYSIS</span></div>
      <form onSubmit={runAnalysis} className="trip-form">
        <div className="location-fields">
          <LocationAutocomplete
            label="ORIGIN"
            value={origin}
            onChange={setOrigin}
            placeholder="City, address or ZIP"
            required
            icon="origin"
          />
          <button
            type="button"
            className="swap-button"
            title="Swap origin and destination"
            onClick={() => {
              setOrigin(destination);
              setDestination(origin);
            }}
          >
            <ArrowDownUp size={16} />
          </button>
          <LocationAutocomplete
            label="DESTINATION"
            value={destination}
            onChange={setDestination}
            placeholder="City, address or ZIP"
            required
            icon="destination"
          />
        </div>
        <div className="parameter-fields">
          <label className="field">
            <span>DEPARTURE DATE & TIME</span>
            <div className="input-wrap">
              <CalendarClock size={17} />
              <input
                type="datetime-local"
                value={departure}
                onChange={event => setDeparture(event.target.value)}
                required
              />
            </div>
          </label>
          <label className="field">
            <span>LOAD WEIGHT (LB)</span>
            <div className="input-wrap">
              <Package size={17} />
              <input
                type="number"
                min="0"
                step="1"
                value={loadWeight}
                onChange={event => setLoadWeight(event.target.value)}
                placeholder="e.g. 35000"
                required
              />
            </div>
          </label>
          <label className="field">
            <span>CHECKPOINT INTERVAL</span>
            <div className="input-wrap select-wrap">
              <Gauge size={17} />
              <select
                value={interval}
                onChange={event => setInterval(event.target.value)}
                style={{ color: interval ? '#e5edf5' : '#607187' }}
                required
              >
                <option value="" disabled>Select interval</option>
                <option value="10">Every 10 miles</option>
                <option value="25">Every 25 miles</option>
                <option value="50">Every 50 miles</option>
              </select>
              <ChevronDown size={15} />
            </div>
          </label>
        </div>
        <div className="form-footer"><span className="form-hint"><ShieldCheck size={14} /> Weather and load-weight risk rules will be applied.</span><button className="primary-button" type="submit" disabled={loading}>{loading ? <><RefreshCw size={16} className="spin" /> ANALYZING ROUTES</> : <>ANALYZE ROUTES <ArrowRight size={16} /></>}</button></div>
      </form>
      {error && <div className="error-banner"><AlertTriangle size={17} />{error}</div>}
    </section>

    {!analysis && <section className="empty-state"><div className="empty-icon"><Compass size={28} /></div><h3>Your next route, made safer.</h3><p>Enter your trip details above to compare up to three driving routes against forecast weather conditions.</p><div className="feature-row"><span><Wind size={15} /> Wind exposure</span><span><CloudDrizzle size={15} /> Rain intensity</span><span><CloudSnow size={15} /> Snowfall risk</span></div></section>}

    {analysis && <>
      <section className="results-header"><div><span className="step-label">02 / ROUTE INTELLIGENCE</span><h2>Route comparison</h2><p>{analysis.input.origin.name} <ArrowRight size={13} /> {analysis.input.destination.name}</p></div><div className="analysis-meta"><span><CalendarClock size={14} /> {formatDate(analysis.input.departure_datetime)} · {formatTime(analysis.input.departure_datetime)}</span><span><Package size={14} /> {analysis.input.load_weight_lb.toLocaleString()} lb payload</span></div></section>
      {recommendedRoute && <section className="recommendation-banner"><div className="recommendation-icon"><ShieldCheck size={21} /></div><div className="recommendation-copy"><span className="recommended-tag">RECOMMENDED ROUTE</span><h3>{recommendedRoute.name} <span>· {formatDuration(recommendedRoute.duration_minutes)}</span></h3><p>{analysis.recommendation?.reason || 'Lowest combined exposure based on the required safety-first ranking.'}</p></div><div className="recommendation-stats"><div><strong>{recommendedRoute.summary.severe_miles.toFixed(1)}</strong><span>SEVERE / NO-TRAVEL MI</span></div><div><strong>{recommendedRoute.summary.high_miles.toFixed(1)}</strong><span>HIGH-RISK MI</span></div></div></section>}
      <section className="map-section panel"><div className="map-section-header"><div><span className="step-label">03 / LIVE ROUTE VIEW</span><h2>Weather corridor</h2></div><button className={`toggle-button ${showHeatmap ? 'active' : ''}`} onClick={() => setShowHeatmap(!showHeatmap)}><span className="toggle-dot" /> WEATHER HEATMAP</button></div>
        <RouteMap analysis={analysis} heatmap={heatmap} selectedRouteId={selectedRouteId} showHeatmap={showHeatmap} onCheckpointSelect={(routeId, checkpointId) => setSelectedCheckpoint({ routeId, checkpointId })} />
        <div className="forecast-control"><div className="forecast-title"><div><span className="step-label">FORECAST TIMELINE</span><strong>{forecastHour === 0 ? 'Departure window' : `+${forecastHour} hours`}</strong></div><span className="forecast-time">{heatmap ? `${formatDate(heatmap.forecast_time)} · ${formatTime(heatmap.forecast_time)}` : 'Loading forecast...'}</span></div><input className="forecast-slider" type="range" min="0" max="48" step="1" value={forecastHour} onChange={event => setForecastHour(Number(event.target.value))} /><div className="slider-labels"><span>NOW / DEPARTURE</span><span>+12H</span><span>+24H</span><span>+36H</span><span>+48H</span></div>{heatmapLoading && <span className="loading-note"><RefreshCw size={12} className="spin" /> Updating forecast layer...</span>}</div>
      </section>
      <section className="route-results"><div className="section-heading"><div><span className="step-label">04 / DECISION SUPPORT</span><h2>Compare your options</h2></div><span className="results-count">{analysis.routes.length} ROUTES FOUND</span></div><div className="route-grid">{analysis.routes.map((route, index) => <RouteCard key={route.id} route={route} index={index} selected={selectedRouteId === route.id} onSelect={() => { setSelectedRouteId(route.id); setSelectedCheckpoint(null); }} />)}</div></section>
      <section className="checkpoint-section panel"><div className="section-heading"><div><span className="step-label">05 / CHECKPOINT FORECAST</span><h2>Weather along the route</h2></div><span className="results-count">{selectedRoute?.checkpoints.length ?? 0} CHECKPOINTS</span></div><div className="checkpoint-route-select">{analysis.routes.map(route => <button key={route.id} className={selectedRouteId === route.id ? 'selected' : ''} onClick={() => { setSelectedRouteId(route.id); setSelectedCheckpoint(null); }}>{route.name}{route.recommended ? ' · BEST' : ''}</button>)}</div>
        <div className="checkpoint-list">{selectedRoute?.checkpoints.map(checkpoint => <CheckpointRow key={checkpoint.id} checkpoint={checkpoint} selected={selectedCheckpoint?.routeId === selectedRoute.id && selectedCheckpoint.checkpointId === checkpoint.id} onClick={() => setSelectedCheckpoint({ routeId: selectedRoute.id, checkpointId: checkpoint.id })} />)}</div>
      </section>
      {selectedCheckpointData && <CheckpointDetail checkpoint={selectedCheckpointData} onClose={() => setSelectedCheckpoint(null)} />}
      <p className="data-note"><AlertTriangle size={13} /> Forecasts are estimates, not live road-condition reports. Always follow local restrictions and official weather alerts. {analysis.forecast_note}</p>
    </>}
    <footer className="footer"><span>STORMROUTE <span className="footer-muted">/ WEATHER-AWARE LOGISTICS</span></span><span>BUILT FOR SAFER MILES <span className="footer-muted">· 2026</span></span></footer>
  </main>;
}

function RouteCard({ route, index, selected, onSelect }: { route: RouteOption; index: number; selected: boolean; onSelect: () => void }) {
  const colorClass = ['teal', 'amber', 'violet'][index % 3];
  return <button className={`route-card ${selected ? 'route-card-selected' : ''}`} onClick={onSelect}>
    <div className="route-card-top"><div className="route-card-name"><span className={`route-index ${colorClass}`}>{String(index + 1).padStart(2, '0')}</span><div><strong>{route.name}</strong><span>{route.distance_miles.toFixed(1)} miles</span></div></div>{route.recommended ? <span className="best-pill"><Check size={12} /> BEST</span> : <span className="rank-pill">RANK #{route.rank}</span>}</div>
    <div className="route-card-time"><strong>{formatDuration(route.duration_minutes)}</strong><span>· ETA {formatTime(route.estimated_arrival)}</span></div>
    <div className="risk-bar" title="Risk mileage distribution">{(['low', 'moderate', 'high', 'severe', 'no_travel'] as const).map(level => { const value = route.summary.risk_miles[level] ?? 0; return value > 0 ? <span key={level} className={`risk-segment ${level}`} style={{ width: `${value / Math.max(route.distance_miles, 1) * 100}%` }} /> : null; })}</div>
    <div className="route-metrics"><div><strong>{route.summary.severe_miles.toFixed(1)}</strong><span>SEVERE MI</span></div><div><strong>{route.summary.high_miles.toFixed(1)}</strong><span>HIGH MI</span></div><div><strong>{route.summary.average_risk_score.toFixed(2)}<small>/4</small></strong><span>AVG RISK</span></div></div>
    <div className="route-card-footer">{selected ? 'CURRENTLY VIEWING' : 'VIEW THIS ROUTE'} <ArrowRight size={14} /></div>
  </button>;
}

function CheckpointRow({ checkpoint, selected, onClick }: { checkpoint: Checkpoint; selected: boolean; onClick: () => void }) {
  const weather = checkpoint.weather;
  const locationLabel = checkpoint.location_name
    ? `Checkpoint ${checkpoint.id} · ${checkpoint.location_name}`
    : `Checkpoint ${checkpoint.id}`;
  return <button className={`checkpoint-row ${selected ? 'checkpoint-selected' : ''}`} onClick={onClick}>
    <div className="checkpoint-mile">
      <span className="checkpoint-pin" />
      <strong>{checkpoint.distance_miles.toFixed(0)} <small>MI</small></strong>
      <span title={locationLabel}>{locationLabel}</span>
    </div>
    <div className="checkpoint-eta"><Clock3 size={14} /><span>{formatTime(checkpoint.arrival_time)}</span><small>ARRIVAL</small></div>
    <div className="checkpoint-weather">{!weather.forecast_available && <span className="forecast-unavailable">Forecast unavailable</span>}<span><Wind size={15} /> {weather.forecast_available ? weather.wind_mph : '—'} <small>mph</small></span><span><CloudDrizzle size={15} /> {weather.forecast_available ? weather.rain_in_per_hour : '—'} <small>in/hr</small></span><span><CloudSnow size={15} /> {weather.forecast_available ? weather.snow_in_per_hour : '—'} <small>in/hr</small></span></div>
    <span className={`risk-pill ${riskColors[checkpoint.risk_level]}`}>{riskLabels[checkpoint.risk_level]}</span><ArrowRight className="checkpoint-arrow" size={15} />
  </button>;
}

function CheckpointDetail({ checkpoint, onClose }: { checkpoint: Checkpoint; onClose: () => void }) {
  const detailTitle = checkpoint.location_name
    ? `Mile ${checkpoint.distance_miles.toFixed(1)} · ${checkpoint.location_name}`
    : `Mile ${checkpoint.distance_miles.toFixed(1)}`;
  return <section className="detail-panel panel"><div className="detail-heading"><div><span className="step-label">CHECKPOINT {checkpoint.id} / CONDITION BREAKDOWN</span><h3>{detailTitle}</h3></div><button onClick={onClose} className="close-button">CLOSE ×</button></div><div className="condition-grid">{Object.entries(checkpoint.risk_by_condition).map(([condition, level]) => <div key={condition} className="condition-card"><span>{condition.toUpperCase()}</span><strong>{riskLabels[level]}</strong><small>{!checkpoint.weather.forecast_available ? 'Forecast unavailable · conservative High risk' : condition === 'wind' ? `${checkpoint.weather.wind_mph} mph` : condition === 'rain' ? `${checkpoint.weather.rain_in_per_hour} in/hr` : `${checkpoint.weather.snow_in_per_hour} in/hr`}</small></div>)}</div><p className="detail-footnote">Forecast hour: {checkpoint.weather.forecast_time ? new Date(checkpoint.weather.forecast_time).toLocaleString() : 'Unavailable'}</p></section>;
}

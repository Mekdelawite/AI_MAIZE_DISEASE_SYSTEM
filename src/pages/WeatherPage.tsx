import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CloudSun, Droplets, MapPin, RefreshCw, Search, Thermometer, Wind } from 'lucide-react';
import { ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { weatherService } from '../services/weatherService';
import { WeatherData } from '../types/api';

export const WeatherPage: React.FC = () => {
  const { t } = useApp();

  const [mode, setMode] = useState<'farmer' | 'city'>('farmer');
  const [cityQuery, setCityQuery] = useState('Addis Ababa');
  const [units, setUnits] = useState<'metric' | 'imperial'>('metric');

  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (mode === 'farmer') {
        const data = await weatherService.getFarmerWeather(units);
        setWeather(data);
      } else {
        if (!cityQuery.trim()) {
          setError('Please enter a city or town name.');
          setLoading(false);
          return;
        }
        const data = await weatherService.getCurrentByCity(cityQuery, units);
        setWeather(data);
      }
    } catch (err: any) {
      setError(err?.message || 'Unable to fetch meteorological data from the server.');
      setWeather(null);
    } finally {
      setLoading(false);
    }
  }, [mode, cityQuery, units]);

  useEffect(() => {
    fetchWeather();
  }, [fetchWeather]);

  const tempUnit = units === 'metric' ? '°C' : '°F';
  const windUnit = units === 'metric' ? 'm/s' : 'mph';

  return (
    <AppShell
      title={t('navWeather')}
      subtitle="Live meteorological conditions from /api/weather/farmer (using saved farm coordinates) or /api/weather/current by city."
      actions={
        <button
          type="button"
          onClick={fetchWeather}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      {/* Controls Bar */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800">
          <button
            type="button"
            onClick={() => setMode('farmer')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
              mode === 'farmer'
                ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                : 'text-stone-600 dark:text-stone-400'
            }`}
          >
            My Farm Coordinates (/api/weather/farmer)
          </button>
          <button
            type="button"
            onClick={() => setMode('city')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
              mode === 'city'
                ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                : 'text-stone-600 dark:text-stone-400'
            }`}
          >
            Search by City (/api/weather/current)
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {mode === 'city' && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                fetchWeather();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={cityQuery}
                onChange={(e) => setCityQuery(e.target.value)}
                placeholder="Enter Ethiopian city (e.g. Jimma, Bahir Dar)"
                className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 min-w-[200px]"
              />
              <button
                type="submit"
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-emerald-800 hover:bg-emerald-700 rounded-lg cursor-pointer"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Lookup</span>
              </button>
            </form>
          )}

          <div className="flex items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800">
            <button
              type="button"
              onClick={() => setUnits('metric')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer ${
                units === 'metric'
                  ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                  : 'text-stone-600 dark:text-stone-400'
              }`}
            >
              Metric (°C)
            </button>
            <button
              type="button"
              onClick={() => setUnits('imperial')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer ${
                units === 'imperial'
                  ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                  : 'text-stone-600 dark:text-stone-400'
              }`}
            >
              Imperial (°F)
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={3} />
      ) : error ? (
        <div className="space-y-4">
          <ErrorState
            title="Weather reading unavailable"
            message={error}
            onRetry={fetchWeather}
          />
          {mode === 'farmer' && (
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2.5 text-stone-700 dark:text-stone-300">
                <MapPin className="w-4 h-4 text-emerald-800 dark:text-emerald-400 shrink-0" />
                <span>
                  Does your farmer profile have saved GPS coordinates? Configure your latitude and longitude in your profile or switch to City Search above.
                </span>
              </div>
              <Link
                to="/farmer/profile"
                className="px-3.5 py-2 font-semibold text-white bg-emerald-900 rounded-lg whitespace-nowrap"
              >
                Configure Profile Coordinates
              </Link>
            </div>
          )}
        </div>
      ) : weather ? (
        <div className="space-y-6">
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
                  <MapPin className="w-3.5 h-3.5" />
                  <span>
                    {weather.city || weather.woreda || weather.region || (mode === 'city' ? cityQuery : 'Saved Farm Coordinates')}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-4">
                  <span className="text-4xl sm:text-5xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                    {weather.temperature ?? weather.temp ?? '—'}
                    {tempUnit}
                  </span>
                  <span className="text-base font-medium text-stone-700 dark:text-stone-300 capitalize">
                    {weather.description || weather.condition || 'Reported condition'}
                  </span>
                </div>
              </div>
              <CloudSun className="w-10 h-10 text-amber-500" />
            </div>

            <div className="mt-8 pt-6 border-t border-stone-200 dark:border-stone-800 grid grid-cols-2 sm:grid-cols-4 gap-6">
              <div>
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Thermometer className="w-3.5 h-3.5" />
                  <span>Feels Like</span>
                </div>
                <p className="mt-1 text-lg font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                  {weather.feels_like !== undefined ? `${weather.feels_like}${tempUnit}` : '—'}
                </p>
              </div>

              <div>
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Droplets className="w-3.5 h-3.5" />
                  <span>Relative Humidity</span>
                </div>
                <p className="mt-1 text-lg font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                  {weather.humidity !== undefined ? `${weather.humidity}%` : '—'}
                </p>
              </div>

              <div>
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Wind className="w-3.5 h-3.5" />
                  <span>Wind Speed</span>
                </div>
                <p className="mt-1 text-lg font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                  {weather.wind_speed !== undefined ? `${weather.wind_speed} ${windUnit}` : '—'}
                </p>
              </div>

              <div>
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Droplets className="w-3.5 h-3.5" />
                  <span>Rainfall / Pressure</span>
                </div>
                <p className="mt-1 text-lg font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                  {weather.rainfall_mm !== undefined
                    ? `${weather.rainfall_mm} mm`
                    : weather.pressure !== undefined
                    ? `${weather.pressure} hPa`
                    : '—'}
                </p>
              </div>
            </div>

            {weather.advisory_note && (
              <div className="mt-6 pt-4 border-t border-stone-200 dark:border-stone-800 text-xs text-stone-700 dark:text-stone-300">
                <span className="font-semibold">Weather Advisory: </span>
                <span>{weather.advisory_note}</span>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </AppShell>
  );
};

import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays,
  Check,
  CloudOff,
  CloudSun,
  CloudRain,
  Droplets,
  Info,
  MapPin,
  RefreshCw,
  Sprout,
  ThermometerSun,
  Wind,
} from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { weatherService } from '../services/weatherService';
import { CropCalendarData, FarmerProfile, FarmerWeatherForecastData, SoilWaterEstimate, WeatherData } from '../types/api';
import { profileService } from '../services/profileService';

export const CropCalendarPage: React.FC = () => {
  const { t, isOnline, language } = useApp();
  const [calendar, setCalendar] = useState<CropCalendarData | null>(null);
  const [calendarLoading, setCalendarLoading] = useState(true);
  const [calendarError, setCalendarError] = useState(false);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);
  const [weatherError, setWeatherError] = useState(false);
  const [forecast, setForecast] = useState<FarmerWeatherForecastData['forecast'] | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState(false);
  const [soilWater, setSoilWater] = useState<SoilWaterEstimate | null>(null);
  const [soilWaterLoading, setSoilWaterLoading] = useState(true);
  const [soilWaterError, setSoilWaterError] = useState(false);
  const [farmInputs, setFarmInputs] = useState<FarmerProfile>({});
  const [inputsSaving, setInputsSaving] = useState(false);
  const [inputsSaved, setInputsSaved] = useState(false);
  const [inputsSaveError, setInputsSaveError] = useState(false);

  const loadCalendar = useCallback(async () => {
    if (!isOnline) {
      setCalendarLoading(false);
      return;
    }

    setCalendarLoading(true);
    setCalendarError(false);
    try {
      setCalendar(await weatherService.getCropCalendar());
    } catch {
      setCalendarError(true);
    } finally {
      setCalendarLoading(false);
    }
  }, [isOnline]);

  const loadSoilWater = useCallback(async () => {
    if (!isOnline) {
      setSoilWaterLoading(false);
      setWeatherLoading(false);
      setForecastLoading(false);
      return;
    }
    setSoilWaterLoading(true);
    setWeatherLoading(true);
    setForecastLoading(true);
    setSoilWaterError(false);
    setWeatherError(false);
    setForecastError(false);
    try {
      const [estimate, profile] = await Promise.all([
        weatherService.getSoilWaterEstimate(),
        profileService.getProfile(),
      ]);
      setSoilWater(estimate);
      setWeather(estimate.current_weather ?? null);
      setForecast(estimate.forecast_data ?? null);
      setWeatherError(!estimate.current_weather);
      setForecastError(!estimate.forecast_data);
      setFarmInputs(profile.farmer_profile ?? {});
    } catch {
      setSoilWaterError(true);
      setWeatherError(true);
      setForecastError(true);
    } finally {
      setSoilWaterLoading(false);
      setWeatherLoading(false);
      setForecastLoading(false);
    }
  }, [isOnline]);

  useEffect(() => {
    void loadCalendar();
    void loadSoilWater();
  }, [loadCalendar, loadSoilWater]);

  const saveFarmInputs = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setInputsSaving(true);
    setInputsSaved(false);
    setInputsSaveError(false);
    try {
      const result = await profileService.updateProfile({
        planting_date: farmInputs.planting_date || null,
        soil_type: farmInputs.soil_type || null,
        available_water_capacity_mm_per_m: farmInputs.available_water_capacity_mm_per_m ?? null,
        crop_growth_stage: farmInputs.crop_growth_stage || null,
        irrigation_status: farmInputs.irrigation_status || null,
        last_irrigation_date: farmInputs.last_irrigation_date || null,
        last_irrigation_mm: farmInputs.last_irrigation_mm ?? null,
      });
      setFarmInputs(result.farmer_profile ?? {});
      setInputsSaved(true);
      await loadSoilWater();
    } catch {
      setInputsSaveError(true);
    } finally {
      setInputsSaving(false);
    }
  };

  const location = calendar?.location;
  const currentStage = calendar?.current_stage;
  const stages = calendar?.calendar ?? [];
  const currentCalendarStageIndex = stages.findIndex((stage) => stage.stage === currentStage?.stage);
  const upcomingCalendarStages = currentCalendarStageIndex >= 0
    ? stages.slice(currentCalendarStageIndex + 1, currentCalendarStageIndex + 2)
    : stages.slice(0, 1);
  const advisoryData = soilWater?.advisories;
  const recommendations = advisoryData?.recommendations ?? [];
  const currentLocale = language === 'am' ? 'am-ET' : 'en-ET';
  const formatDate = (value: string, options: Intl.DateTimeFormatOptions) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(currentLocale, options);
  };
  const formatDateTime = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? value
      : date.toLocaleString(currentLocale, { dateStyle: 'medium', timeStyle: 'short' });
  };
  const weatherCondition = (code: number | null) => {
    if (code === null) return t('calendarUnavailable');
    if (code === 0) return t('calendarConditionClear');
    if (code <= 3) return t('calendarConditionCloudy');
    if (code === 45 || code === 48) return t('calendarConditionFog');
    if (code >= 51 && code <= 67) return t('calendarConditionRain');
    if (code >= 71 && code <= 77) return t('calendarConditionSnow');
    if (code >= 80 && code <= 82) return t('calendarConditionShowers');
    if (code >= 95) return t('calendarConditionThunderstorm');
    return t('calendarUnavailable');
  };
  const hasPrecipitationData = Boolean(forecast?.days.length) && forecast!.days.every((day) => day.precipitation_mm !== null);
  const hasForecastRain = forecast?.days.some((day) => day.precipitation_mm !== null && day.precipitation_mm > 0) ?? false;
  const referenceDate = calendar?.reference_date
    ? new Date(calendar.reference_date).toLocaleDateString(currentLocale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : null;

  return (
    <AppShell
      title={t('navCalendar')}
      subtitle={t('calendarSubtitle')}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              void loadCalendar();
              void loadSoilWater();
            }}
            disabled={!isOnline || calendarLoading || soilWaterLoading}
            className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-stone-300 bg-white px-3.5 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200 dark:hover:bg-stone-800"
          >
            <RefreshCw className={`h-4 w-4 ${calendarLoading || soilWaterLoading ? 'animate-spin' : ''}`} />
            <span>{t('refresh')}</span>
          </button>
          <Link
            to="/farmer/profile"
            className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-emerald-800 px-3.5 text-sm font-semibold text-white transition hover:bg-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600"
          >
            <MapPin className="h-4 w-4" />
            <span>{t('calendarUpdateLocation')}</span>
          </Link>
        </div>
      }
    >
      <div className="space-y-6">
        {!isOnline && (
          <div className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
            <CloudOff className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{t('calendarOffline')}</p>
          </div>
        )}

        {((calendarError && calendar) || (weatherError && weather) || (forecastError && forecast) || (!isOnline && (calendar || weather || forecast))) && (
          <div role="status" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
            {t('calendarShowingPrevious')}
          </div>
        )}

        {calendarLoading && !calendar ? (
          <div className="space-y-4" role="status" aria-live="polite" aria-label={t('calendarLoading')}>
            <div className="h-48 animate-pulse rounded-3xl bg-stone-200 dark:bg-stone-800" />
            <div className="grid gap-4 md:grid-cols-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-36 animate-pulse rounded-2xl bg-stone-200 dark:bg-stone-800" />
              ))}
            </div>
            <div className="h-64 animate-pulse rounded-3xl bg-stone-200 dark:bg-stone-800" />
          </div>
        ) : calendarError && !calendar ? (
          <section role="alert" className="rounded-3xl border border-red-200 bg-red-50 p-6 dark:border-red-900/60 dark:bg-red-950/20">
            <div className="flex items-start gap-3">
              <Info className="mt-0.5 h-5 w-5 shrink-0 text-red-700 dark:text-red-400" />
              <div>
                <h2 className="font-semibold text-red-950 dark:text-red-100">{t('calendarLoadFailed')}</h2>
                <button
                  type="button"
                  onClick={() => void loadCalendar()}
                  disabled={!isOnline}
                  className="mt-4 rounded-xl bg-red-800 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {t('calendarTryAgain')}
                </button>
              </div>
            </div>
          </section>
        ) : !calendar ? (
          <section className="rounded-3xl border border-stone-200 bg-white p-8 text-center dark:border-stone-800 dark:bg-[#121A16]">
            <CalendarDays className="mx-auto h-9 w-9 text-stone-400" />
            <h2 className="mt-3 text-lg font-bold text-stone-900 dark:text-stone-100">{t('calendarEmptyTitle')}</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-stone-600 dark:text-stone-400">{!isOnline ? t('calendarOfflineNoCache') : t('calendarEmptyDescription')}</p>
          </section>
        ) : (
          <>
            <section className="relative overflow-hidden rounded-[1.75rem] bg-[#14532D] p-5 text-white shadow-[0_14px_36px_rgba(20,83,45,0.16)] sm:p-8">
              <div className="relative grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/25 bg-white/10 px-3 py-1.5 text-xs font-semibold text-emerald-100">
                    <Sprout className="h-4 w-4" />
                    {calendar.crop} · {calendar.country}
                  </div>
                  <p className="mt-6 text-sm font-semibold uppercase tracking-[0.16em] text-lime-200">{t('calendarCurrentStage')}</p>
                  <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{currentStage?.label ?? t('calendarUnavailable')}</h2>
                  {currentStage && (
                    <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-emerald-100">
                      <span className="rounded-full bg-white/10 px-3 py-1.5">{currentStage.month_name}</span>
                      <span>{currentStage.activities?.[0]}</span>
                    </div>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                    <div className="flex items-center gap-2 text-emerald-100">
                      <MapPin className="h-4 w-4" />
                      <span className="text-xs font-semibold uppercase tracking-wide">{t('calendarLocation')}</span>
                    </div>
                    <p className="mt-3 text-base font-semibold">{location?.region || t('calendarUnavailable')}</p>
                    <p className="mt-1 text-sm text-emerald-100/80">{location?.woreda || t('calendarNoWoreda')}</p>
                    {location?.kebele && <p className="mt-1 text-xs text-emerald-100/70">{location.kebele}</p>}
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                    <div className="flex items-center gap-2 text-emerald-100">
                      <CalendarDays className="h-4 w-4" />
                      <span className="text-xs font-semibold uppercase tracking-wide">{t('calendarSeason')}</span>
                    </div>
                    <p className="mt-3 text-base font-semibold">{calendar.season}</p>
                    {referenceDate && <p className="mt-1 text-xs text-emerald-100/70">{referenceDate}</p>}
                  </div>
                </div>
              </div>
            </section>

            <section aria-label={t('calendarOverview')} className="grid gap-4 md:grid-cols-3">
              <article className="farmer-card min-w-0 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold text-stone-700 dark:text-stone-200">
                    <CloudSun className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    {t('calendarWeather')}
                  </div>
                  {weather && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">{weather.location || t('calendarWeather')}</span>}
                </div>
                {weatherLoading && !weather ? (
                  <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">{t('loading')}</p>
                ) : weather ? (
                  <>
                    <div className="mt-5 flex items-center gap-3">
                      <ThermometerSun className="h-8 w-8 text-orange-500" />
                      <span className="text-3xl font-bold tracking-tight text-stone-950 dark:text-white">
                        {weather.temperature ?? t('calendarUnavailableShort')}{weather.temperature !== undefined ? '°C' : ''}
                      </span>
                    </div>
                    <p className="mt-2 capitalize text-sm text-stone-600 dark:text-stone-300">{weather.description || t('calendarUnavailable')}</p>
                    {weather.timestamp && <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">{t('calendarWeatherUpdated')}: {formatDateTime(weather.timestamp)}</p>}
                    <div className="mt-5 grid grid-cols-2 gap-3 border-t border-stone-100 pt-4 dark:border-stone-800">
                      <div className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-300">
                        <Droplets className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                        <span>{t('calendarHumidity')}: {weather.humidity !== undefined ? `${weather.humidity}%` : t('calendarUnavailableShort')}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-300">
                        <Wind className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                        <span>{t('calendarWind')}: {weather.wind_speed !== undefined ? `${weather.wind_speed} m/s` : t('calendarUnavailableShort')}</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="mt-4 text-sm text-stone-600 dark:text-stone-400">{weatherError ? t('calendarWeatherUnavailable') : t('calendarUnavailable')}</p>
                )}
                {weather?.rainfall_mm !== undefined && <p className="mt-3 text-sm text-stone-600 dark:text-stone-300">{t('calendarPrecipitation')}: {weather.rainfall_mm} mm{weather.rainfall_period_hours ? ` (${weather.rainfall_period_hours}h)` : ''}</p>}
                <p className="mt-4 text-xs leading-relaxed text-stone-500 dark:text-stone-400">{t('calendarWeatherDataNote')}</p>
              </article>

              <article className="farmer-card min-w-0 p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-stone-700 dark:text-stone-200">
                    <CloudSun className="h-5 w-5 text-sky-600 dark:text-sky-400" />
                    {t('calendarForecast')}
                  </div>
                  <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-800 dark:bg-sky-950/50 dark:text-sky-300">{t('calendarSevenDayForecast')}</span>
                </div>
                {forecastLoading && !forecast ? (
                  <p className="mt-5 text-sm text-stone-500 dark:text-stone-400" role="status">{t('loading')}</p>
                ) : forecast?.days.length ? (
                  <>
                    {forecast.provider_timestamp && <p className="mt-3 text-xs text-stone-500 dark:text-stone-400">{t('calendarForecastUpdated')}: {forecast.provider_timestamp.replace('T', ' ')}{forecast.timezone_abbreviation ? ` ${forecast.timezone_abbreviation}` : ''}</p>}
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                      {forecast.days.map((day) => (
                        <article key={day.date} className="rounded-xl border border-stone-200 bg-stone-50/80 p-3 dark:border-stone-800 dark:bg-stone-900/60">
                          <div className="flex items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold text-stone-900 dark:text-white">{formatDate(day.date, { weekday: 'short', month: 'short', day: 'numeric' })}</h3>
                            <span className="text-xs text-stone-600 dark:text-stone-300">{weatherCondition(day.weather_code)}</span>
                          </div>
                          <p className="mt-2 text-sm font-semibold text-stone-800 dark:text-stone-100">
                            {day.temperature_min !== null ? `${day.temperature_min}°` : t('calendarUnavailableShort')} – {day.temperature_max !== null ? `${day.temperature_max}°C` : t('calendarUnavailableShort')}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-stone-600 dark:text-stone-400">
                            {day.precipitation_mm !== null && <span className="inline-flex items-center gap-1"><CloudRain className="h-3.5 w-3.5" />{day.precipitation_mm} mm</span>}
                            {day.precipitation_probability !== null && <span>{t('calendarForecastProbability')}: {day.precipitation_probability}%</span>}
                            {day.wind_speed_max !== null && <span>{t('calendarForecastWind')}: {day.wind_speed_max} km/h</span>}
                          </div>
                        </article>
                      ))}
                    </div>
                    <p className="mt-4 text-xs leading-relaxed text-stone-500 dark:text-stone-400">{t('calendarForecastNote')}</p>
                  </>
                ) : (
                  <p className="mt-5 text-sm leading-relaxed text-stone-600 dark:text-stone-400">
                    {!isOnline ? t('calendarForecastOffline') : forecastError ? t('calendarForecastError') : t('calendarForecastUnavailable')}
                  </p>
                )}
              </article>

              <article className="farmer-card min-w-0 p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-stone-700 dark:text-stone-200">
                  <Droplets className="h-5 w-5 text-teal-700 dark:text-teal-400" />
                  {t('calendarSoilMoisture')}
                </div>
                <p className="mt-2 text-xs font-semibold text-teal-800 dark:text-teal-300">{t('soilWaterLabel')}</p>
                {soilWaterLoading && !soilWater ? <p className="mt-4 text-sm text-stone-500" role="status">{t('soilWaterLoading')}</p> : soilWater ? (
                  <>
                    <p className="mt-4 text-sm font-semibold text-stone-600 dark:text-stone-300">{soilWater.root_zone ? t('soilWaterAvailable') : t('soilWaterRisk')}</p>
                    <p className="mt-1 text-2xl font-bold text-stone-950 dark:text-white">
                      {soilWater.root_zone ? `${soilWater.root_zone.available_water_mm} / ${soilWater.root_zone.total_available_water_mm} mm` : soilWater.weather_dryness_signal === 'net_deficit' ? t('soilWaterDeficit') : soilWater.weather_dryness_signal === 'net_surplus' ? t('soilWaterSurplus') : t('calendarUnavailable')}
                    </p>
                    {soilWater.historical.rainfall_mm !== null && soilWater.historical.rainfall_mm !== undefined && <p className="mt-3 text-sm text-stone-600 dark:text-stone-300">{t('soilWaterHistorical')}: {t('soilWaterRain')} {soilWater.historical.rainfall_mm} mm · ET₀ {soilWater.historical.et0_mm ?? t('calendarUnavailableShort')} mm</p>}
                    {soilWater.historical.net_water_balance_mm !== null && soilWater.historical.net_water_balance_mm !== undefined && <p className="mt-2 text-sm text-stone-600 dark:text-stone-300">{t('soilWaterNetBalance')}: {soilWater.historical.net_water_balance_mm} mm</p>}
                    {soilWater.forecast.rainfall_mm !== null && soilWater.forecast.rainfall_mm !== undefined && <p className="mt-2 text-sm text-stone-600 dark:text-stone-300">{t('soilWaterForecast')}: {t('soilWaterRain')} {soilWater.forecast.rainfall_mm} mm · ET₀ {soilWater.forecast.et0_mm ?? t('calendarUnavailableShort')} mm</p>}
                    <p className="mt-3 text-xs text-stone-500 dark:text-stone-400">{t('soilWaterStage')}: {soilWater.crop_growth_stage ? t(`soilWaterStage${soilWater.crop_growth_stage === 'mid_season' ? 'Mid' : soilWater.crop_growth_stage === 'late_season' ? 'Late' : soilWater.crop_growth_stage === 'initial' ? 'Initial' : 'Development'}`) : t('calendarUnavailable')}</p>
                    <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">{t('soilWaterCalcTime')}: {formatDateTime(soilWater.calculated_at)}</p>
                    <p className="mt-2 text-xs font-medium text-amber-800 dark:text-amber-300">{soilWater.reliability === 'low' ? t('soilWaterReliabilityLow') : t('soilWaterReliabilityModerate')}{soilWater.historical.stale ? ` · ${t('soilWaterStale')}` : ''}</p>
                    {soilWater.missing_inputs.length > 0 && <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">{t('soilWaterMissing')}: {soilWater.missing_inputs.map((item) => t(`soilWaterMissing${item === 'planting_date' ? 'Planting' : item === 'growth_stage' ? 'Stage' : item === 'awc' ? 'Awc' : item === 'historical_weather' ? 'Historical' : item === 'complete_weather' ? 'Complete' : item === 'history_window' ? 'Window' : 'Irrigation'}`)).join(', ')}</p>}
                    <div className="mt-3 border-t border-stone-100 pt-3 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-400">
                      <p className="font-semibold">{t('soilWaterSources')}</p>
                      <p className="mt-1">{t('soilWaterHistorical')}: {soilWater.historical.source || t('calendarUnavailable')}</p>
                      <p>{t('soilWaterForecast')}: {soilWater.forecast.source || t('calendarUnavailable')}</p>
                    </div>
                    <details className="mt-3 text-xs text-stone-500 dark:text-stone-400">
                      <summary className="cursor-pointer font-semibold">{t('soilWaterAssumptions')}</summary>
                      <ul className="mt-2 list-disc space-y-1 pl-5">{soilWater.assumptions.map((assumption) => <li key={assumption}>{t(`soilWaterAssumption${assumption === 'reanalysis' ? 'Reanalysis' : assumption === 'kc_stage' ? 'Kc' : assumption === 'initial_storage' ? 'Storage' : assumption === 'irrigation_unreported' ? 'Irrigation' : 'Rain'}`)}</li>)}</ul>
                    </details>
                    <p className="mt-3 text-xs leading-relaxed text-stone-500 dark:text-stone-400">{t(soilWater.recommendation === 'monitor_dryness' ? 'soilWaterAdviceDry' : soilWater.recommendation === 'monitor_drainage' ? 'soilWaterAdviceWet' : 'soilWaterAdvice')} {t('soilWaterNotSensor')}</p>
                  </>
                ) : <p className="mt-4 text-sm leading-relaxed text-stone-600 dark:text-stone-400">{!isOnline ? t('soilWaterUnavailableOffline') : soilWaterError ? t('soilWaterUnavailable') : farmInputs.latitude == null || farmInputs.longitude == null ? t('soilWaterNoCoordinates') : t('soilWaterUnavailable')}</p>}
              </article>
            </section>

            <section className="farmer-card min-w-0 p-5 sm:p-6">
              <div className="mb-4">
                <h2 className="text-lg font-bold text-stone-950 dark:text-white">{t('soilWaterInputs')}</h2>
                <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t('soilWaterNotSensor')}</p>
              </div>
              <form onSubmit={saveFarmInputs} className="farmer-form grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterPlantingDate')}<input type="date" value={farmInputs.planting_date ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, planting_date: event.target.value || null }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900" /></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterSoilType')}<select value={farmInputs.soil_type ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, soil_type: event.target.value || null }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"><option value="">{t('calendarUnavailable')}</option>{['sand','loamy_sand','sandy_loam','loam','silt_loam','silt','sandy_clay_loam','clay_loam','silty_clay_loam','sandy_clay','silty_clay','clay'].map((soil) => <option key={soil} value={soil}>{t(`soilWaterTexture${soil.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join('')}`)}</option>)}</select></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterAwc')}<input type="number" min="1" max="300" step="0.1" value={farmInputs.available_water_capacity_mm_per_m ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, available_water_capacity_mm_per_m: event.target.value ? Number(event.target.value) : null }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900" /><span className="mt-1 block text-xs font-normal text-stone-500 dark:text-stone-400">{t('soilWaterAwcHelp')}</span></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterStage')}<select value={farmInputs.crop_growth_stage ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, crop_growth_stage: (event.target.value || null) as FarmerProfile['crop_growth_stage'] }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"><option value="">{t('calendarUnavailable')}</option><option value="initial">{t('soilWaterStageInitial')}</option><option value="development">{t('soilWaterStageDevelopment')}</option><option value="mid_season">{t('soilWaterStageMid')}</option><option value="late_season">{t('soilWaterStageLate')}</option></select></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterIrrigation')}<select value={farmInputs.irrigation_status ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, irrigation_status: (event.target.value || null) as FarmerProfile['irrigation_status'] }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"><option value="">{t('calendarUnavailable')}</option><option value="unknown">{t('soilWaterIrrigationUnknown')}</option><option value="rainfed">{t('soilWaterRainfed')}</option><option value="irrigated">{t('soilWaterIrrigated')}</option></select></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterLastIrrigation')}<input type="date" value={farmInputs.last_irrigation_date ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, last_irrigation_date: event.target.value || null }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900" /></label>
                <label className="text-sm font-medium text-stone-700 dark:text-stone-200">{t('soilWaterLastIrrigationMm')}<input type="number" min="0.1" max="200" step="0.1" value={farmInputs.last_irrigation_mm ?? ''} onChange={(event) => setFarmInputs((p) => ({ ...p, last_irrigation_mm: event.target.value ? Number(event.target.value) : null }))} className="mt-1 block w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900" /></label>
                <div className="flex flex-col items-start justify-end gap-2"><button type="submit" disabled={inputsSaving || !isOnline} className="min-h-10 rounded-xl bg-emerald-800 px-4 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">{inputsSaving ? t('loading') : t('soilWaterSave')}</button>{inputsSaved && <span role="status" className="text-sm text-emerald-800 dark:text-emerald-300">{t('soilWaterSaved')}</span>}{inputsSaveError && <span role="alert" className="text-sm text-red-700 dark:text-red-300">{t('soilWaterSaveError')}</span>}</div>
              </form>
            </section>

            {forecast?.days.length && hasPrecipitationData && (
              <section className="rounded-2xl border border-sky-200 bg-sky-50/80 p-5 dark:border-sky-900/60 dark:bg-sky-950/20" aria-live="polite">
                <div className="flex items-start gap-3">
                  <Info className="mt-0.5 h-5 w-5 shrink-0 text-sky-800 dark:text-sky-300" />
                  <div>
                    <h2 className="font-semibold text-sky-950 dark:text-sky-100">{t('calendarWeatherGuidance')}</h2>
                    <p className="mt-1 text-sm leading-relaxed text-sky-950/80 dark:text-sky-100/80">
                      {hasForecastRain ? t('calendarRainGuidance') : t('calendarNoRainGuidance')}
                    </p>
                  </div>
                </div>
              </section>
            )}

            <section className="farmer-card min-w-0 p-5 sm:p-6" aria-labelledby="agricultural-advisories-title">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800 dark:text-emerald-400">{t('advisoryToday')}</p>
                  <h2 id="agricultural-advisories-title" className="mt-1 text-xl font-bold text-stone-950 dark:text-white">{t('advisoryRecommendationsTitle')}</h2>
                  <p className="mt-1 max-w-3xl text-sm leading-relaxed text-stone-600 dark:text-stone-400">{t('advisoryRecommendationsIntro')}</p>
                </div>
                {advisoryData?.stage && (
                  <div className="rounded-xl bg-emerald-50 px-3.5 py-2.5 dark:bg-emerald-950/30">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">{t('advisoryCurrentStage')}</p>
                    <p className="mt-1 text-sm font-semibold text-stone-900 dark:text-stone-100">{t(advisoryData.stage.stage_key)}</p>
                    <p className="text-xs text-stone-600 dark:text-stone-400">{t(advisoryData.stage.basis === 'farmer_confirmed' ? 'advisoryStageConfirmed' : 'advisoryStageEstimated')}</p>
                  </div>
                )}
              </div>

              {advisoryData?.stage.comparison && (
                <p className="mt-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm leading-relaxed text-sky-950 dark:border-sky-900/60 dark:bg-sky-950/20 dark:text-sky-100">
                  {t(advisoryData.stage.comparison.explanation_key)} {t('advisoryConfirmedStage')}: {t(advisoryData.stage.comparison.confirmed_stage_key)}. {t('advisoryCalendarEstimate')}: {t(advisoryData.stage.comparison.calendar_stage_key)}.
                </p>
              )}

              {soilWaterLoading ? (
                <p role="status" className="mt-5 text-sm text-stone-500 dark:text-stone-400">{t('advisoryLoading')}</p>
              ) : recommendations.length === 0 ? (
                <p className="mt-5 rounded-xl bg-stone-50 p-4 text-sm text-stone-600 dark:bg-stone-900 dark:text-stone-400">{t('advisoryNoRecommendations')}</p>
              ) : (
                <div className="mt-5 grid gap-4 xl:grid-cols-2">
                  {recommendations.map((item) => (
                    <article key={item.id} className="rounded-xl border border-stone-200 bg-stone-50/70 p-4 dark:border-stone-700 dark:bg-stone-900/60">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:bg-stone-800 dark:text-emerald-300">{t(item.category === 'crop_stage' ? 'advisoryCategoryStage' : item.category === 'weather' ? 'advisoryCategoryWeather' : 'advisoryCategorySoilWater')}</span>
                        <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-amber-950 dark:bg-amber-950/50 dark:text-amber-200">{t(item.priority_key)}</span>
                        <span className="text-[11px] text-stone-500 dark:text-stone-400">{t(item.timing_key)}</span>
                      </div>
                      <h3 className="mt-3 text-base font-bold text-stone-950 dark:text-white">{t(item.title_key)}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-stone-700 dark:text-stone-300">{t(item.explanation_key)}</p>
                      <div className="mt-3 rounded-lg border-l-2 border-emerald-600 bg-white px-3 py-2.5 dark:bg-stone-800/70">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">{t('advisoryAction')}</p>
                        <p className="mt-1 text-sm leading-relaxed text-stone-800 dark:text-stone-200">{t(item.action_key)}</p>
                      </div>
                      <p className="mt-3 text-xs leading-relaxed text-stone-600 dark:text-stone-400"><span className="font-semibold">{t('advisoryWhy')}:</span> {t(item.reason_key)}</p>
                      <p className="mt-2 text-xs text-stone-600 dark:text-stone-400"><span className="font-semibold">{t('advisoryRelevantStage')}:</span> {t(item.stage_key)} · {t(item.stage_basis === 'farmer_confirmed' ? 'advisoryStageConfirmed' : 'advisoryStageEstimated')}</p>
                      {item.supporting_data.length > 0 && (
                        <ul className="mt-3 flex flex-wrap gap-2" aria-label={t('advisorySupportingData')}>
                          {item.supporting_data.map((datum, index) => (
                            <li key={`${datum.label_key}-${index}`} className="rounded-lg bg-white px-2.5 py-1.5 text-xs text-stone-700 dark:bg-stone-800 dark:text-stone-300">{t(datum.label_key)}: <strong>{datum.value}{datum.unit ? ` ${datum.unit}` : ''}</strong></li>
                          ))}
                        </ul>
                      )}
                      <div className="mt-3 border-t border-stone-200 pt-3 dark:border-stone-700">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-stone-500 dark:text-stone-400">{t('advisoryReliability')}: {t(item.reliability_key)}</p>
                        <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs">
                          {item.sources.map((source) => (
                            <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer" className="text-emerald-800 underline decoration-emerald-500/40 underline-offset-2 hover:decoration-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:text-emerald-300">{t(source.key)}</a></li>
                          ))}
                        </ul>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                <h3 className="text-xs font-bold uppercase tracking-wide text-emerald-950 dark:text-emerald-100">{t('calendarScheduledReminders')}</h3>
                {(calendar?.upcoming_reminders ?? []).length > 0 ? (
                  <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                    {calendar!.upcoming_reminders!.map((reminder) => (
                      <li key={reminder.activity_key} className="rounded-xl border border-emerald-200/80 bg-white p-3 dark:border-emerald-900/60 dark:bg-[#121A16]">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="text-sm font-semibold text-stone-900 dark:text-stone-100">{language === 'am' ? reminder.title_am : reminder.title}</p>
                          <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-semibold text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-200">{t(reminder.status === 'sent' ? 'calendarReminderSent' : 'calendarReminderScheduled')}</span>
                        </div>
                        <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">{formatDate(reminder.scheduled_date, { dateStyle: 'medium' })}</p>
                        {reminder.is_read !== null && <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{t(reminder.is_read ? 'calendarReminderRead' : 'calendarReminderUnread')}</p>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-400">{farmInputs.planting_date ? t('calendarNoUpcomingReminders') : t('calendarRemindersNeedPlantingDate')}</p>
                )}
              </div>

              {upcomingCalendarStages.length > 0 && (
                <div className="mt-5 rounded-xl border border-sky-200 bg-sky-50/70 p-4 dark:border-sky-900/60 dark:bg-sky-950/20">
                  <h3 className="text-xs font-bold uppercase tracking-wide text-sky-950 dark:text-sky-100">{t('advisoryUpcomingActivities')}</h3>
                  {upcomingCalendarStages.map((stage) => (
                    <div key={stage.stage} className="mt-2">
                      <p className="text-sm font-semibold text-sky-950 dark:text-sky-100">{stage.label}</p>
                      <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-sky-950/80 dark:text-sky-100/80">
                        {(stage.activities ?? []).slice(0, 3).map((activity, index) => <li key={`${stage.stage}-${index}`} className="flex gap-2"><span aria-hidden="true">•</span><span>{activity}</span></li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {advisoryData?.missing_data_keys?.length ? (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
                  <h3 className="text-xs font-bold uppercase tracking-wide text-amber-950 dark:text-amber-100">{t('advisoryUnavailableInputs')}</h3>
                  <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs leading-relaxed text-amber-950/80 dark:text-amber-100/80">
                    {advisoryData.missing_data_keys.map((key) => <li key={key}>{t(key)}</li>)}
                  </ul>
                </div>
              ) : null}
              {advisoryData && <p className="mt-4 text-xs leading-relaxed text-stone-500 dark:text-stone-400">{t(advisoryData.method_key)} {t(advisoryData.disclaimer_key)}</p>}
            </section>

            <section className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 dark:border-emerald-900/60 dark:bg-emerald-950/20 sm:p-6">
              <div className="flex items-start gap-3">
                <Info className="mt-0.5 h-5 w-5 shrink-0 text-emerald-800 dark:text-emerald-300" />
                <div>
                  <h2 className="font-semibold text-emerald-950 dark:text-emerald-100">{t('calendarRegionalGuidance')}</h2>
                  <p className="mt-1 text-sm leading-relaxed text-emerald-950/80 dark:text-emerald-100/80">{calendar.regional_guidance}</p>
                  <p className="mt-3 text-xs leading-relaxed text-emerald-900/70 dark:text-emerald-200/70">{t('calendarGuideNote')}</p>
                </div>
              </div>
            </section>

            <section>
              <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800 dark:text-emerald-400">{t('calendarOverview')}</p>
                  <h2 className="mt-1 text-2xl font-bold tracking-tight text-stone-950 dark:text-white">{t('calendarActivities')}</h2>
                </div>
                {referenceDate && <p className="text-xs text-stone-500 dark:text-stone-400">{referenceDate}</p>}
              </div>

              {stages.length === 0 ? (
                <div className="rounded-2xl border border-stone-200 bg-white p-6 text-sm text-stone-600 dark:border-stone-800 dark:bg-[#121A16] dark:text-stone-400">{t('calendarEmptyDescription')}</div>
              ) : (
                <ol className="relative space-y-4 border-l-2 border-emerald-100 pl-5 dark:border-emerald-950 sm:space-y-5">
                  {stages.map((stage, index) => {
                    const isCurrent = stage.stage === currentStage?.stage;
                    return (
                      <li
                        key={stage.stage}
                        className="relative min-w-0"
                      >
                        <span className={`absolute -left-[1.68rem] top-5 flex h-5 w-5 items-center justify-center rounded-full ring-4 ring-[#F7F8F4] dark:ring-[#0C1310] ${isCurrent ? 'bg-[#22A06B]' : 'bg-stone-300 dark:bg-stone-700'}`}>
                          {isCurrent && <span className="h-2 w-2 rounded-full bg-white" />}
                        </span>
                        <article className={`farmer-card min-w-0 p-4 transition sm:p-5 ${isCurrent ? 'border-emerald-500 dark:border-emerald-500' : ''}`}>
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-xs font-bold uppercase tracking-[0.14em] text-stone-500 dark:text-stone-400">{t('calendarStage')} {String(index + 1).padStart(2, '0')}</span>
                            {isCurrent && <span className="inline-flex items-center gap-1 rounded-full bg-lime-100 px-2.5 py-1 text-xs font-semibold text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-200"><Check className="h-3.5 w-3.5" />{t('calendarCurrentStage')}</span>}
                          </div>
                          <h3 className="mt-3 break-words text-lg font-bold text-stone-950 dark:text-white sm:text-xl">{stage.label}</h3>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {stage.months.map((month) => (
                              <span key={month} className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700 dark:bg-stone-800 dark:text-stone-200">{month}</span>
                            ))}
                          </div>
                          {stage.activities && stage.activities.length > 0 && (
                            <div className="mt-4 border-t border-stone-100 pt-4 dark:border-stone-800">
                              <p className="mb-3 text-xs font-bold uppercase tracking-wide text-stone-500 dark:text-stone-400">{t('calendarActivities')}</p>
                              <ul className="space-y-2.5">
                                {stage.activities.map((activity, activityIndex) => (
                                  <li key={`${stage.stage}-${activityIndex}`} className="flex items-start gap-2.5 text-sm leading-relaxed text-stone-700 dark:text-stone-300">
                                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-400" />
                                    <span>{activity}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </article>
                      </li>
                    );
                  })}
                </ol>
              )}
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
};

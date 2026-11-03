"""Weather integrations: OpenWeather current conditions and Open-Meteo forecast/archive."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
import time
import requests
from backend.app.config import Config


_CACHE_LOCK = threading.Lock()
_RESPONSE_CACHE: dict[tuple, tuple[float, dict]] = {}
_UNAVAILABLE_UNTIL: dict[str, float] = {}
_CACHE_MAX_ENTRIES = 512
_UNAVAILABLE_COOLDOWN_SECONDS = 60


class WeatherService:
    @staticmethod
    def _validated_current_weather(data: dict) -> dict:
        weather = WeatherService._format_weather_response(data)
        if not isinstance(weather.get("temperature"), (int, float)) or not weather.get("weather"):
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["openweather"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("OpenWeather returned incomplete current conditions.")
        return weather

    @staticmethod
    def _get_json(provider: str, url: str, params: dict, *, cache_seconds: int) -> dict:
        """Fetch provider JSON with bounded retries, caching, and a short circuit break."""
        key = (provider, url, tuple(sorted(params.items())))
        now = time.monotonic()
        with _CACHE_LOCK:
            cached = _RESPONSE_CACHE.get(key)
            if cached and cached[0] > now:
                return deepcopy(cached[1])
            unavailable_until = _UNAVAILABLE_UNTIL.get(provider, 0)
            if unavailable_until > now:
                raise requests.RequestException(
                    f"{provider} weather service is temporarily unavailable."
                )

        for attempt in range(2):
            try:
                response = requests.get(url, params=params, timeout=(2, 3))
                if response.status_code >= 500 and attempt == 0:
                    time.sleep(0.2)
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Weather provider returned a non-object response.")
                with _CACHE_LOCK:
                    _UNAVAILABLE_UNTIL.pop(provider, None)
                    _RESPONSE_CACHE[key] = (time.monotonic() + cache_seconds, data)
                    if len(_RESPONSE_CACHE) > _CACHE_MAX_ENTRIES:
                        oldest = min(_RESPONSE_CACHE, key=lambda item: _RESPONSE_CACHE[item][0])
                        _RESPONSE_CACHE.pop(oldest, None)
                return deepcopy(data)
            except requests.exceptions.SSLError:
                # A certificate failure is not transient; retrying it adds delay without benefit.
                with _CACHE_LOCK:
                    _UNAVAILABLE_UNTIL[provider] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
                raise
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                with _CACHE_LOCK:
                    _UNAVAILABLE_UNTIL[provider] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
                raise requests.RequestException(f"{provider} weather service is unavailable.") from exc
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (401, 429) or (status is not None and status >= 500):
                    with _CACHE_LOCK:
                        _UNAVAILABLE_UNTIL[provider] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
                raise
            except (requests.exceptions.JSONDecodeError, ValueError) as exc:
                with _CACHE_LOCK:
                    _UNAVAILABLE_UNTIL[provider] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
                raise requests.RequestException(f"{provider} returned an invalid weather response.") from exc
            except requests.RequestException:
                raise

        raise requests.RequestException(f"{provider} weather service is unavailable.")

    @staticmethod
    def _format_weather_response(data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Weather provider returned an invalid response.")
        items = data.get("weather")
        items = items if isinstance(items, list) and items and isinstance(items[0], dict) else [{}]
        rain = data.get("rain") if isinstance(data.get("rain"), dict) else {}
        main = data.get("main") if isinstance(data.get("main"), dict) else {}
        sys_data = data.get("sys") if isinstance(data.get("sys"), dict) else {}
        coord = data.get("coord") if isinstance(data.get("coord"), dict) else {}
        wind = data.get("wind") if isinstance(data.get("wind"), dict) else {}
        try:
            timestamp = datetime.fromtimestamp(data["dt"], tz=timezone.utc).isoformat() if isinstance(data.get("dt"), (int, float)) else None
        except (OSError, OverflowError, ValueError):
            timestamp = None
        period = next((hours for hours in (1, 3) if isinstance(rain.get(f"{hours}h"), (int, float))), None)
        result = {
            "location": data.get("name"), "country": sys_data.get("country"),
            "latitude": coord.get("lat"), "longitude": coord.get("lon"),
            "temperature": main.get("temp"), "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"), "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"), "weather": items[0].get("main"),
            "description": items[0].get("description"), "icon": items[0].get("icon"),
            "timestamp": timestamp,
        }
        if period is not None:
            result.update(rainfall_mm=rain[f"{period}h"], rainfall_period_hours=period)
        return result

    @staticmethod
    def _coordinates(latitude, longitude):
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError):
            raise ValueError("Latitude and longitude must be valid numbers.")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are outside valid ranges.")
        return latitude, longitude

    @staticmethod
    def get_current_weather(city: str, units: str = "metric") -> dict:
        if not Config.WEATHER_API_KEY:
            raise ValueError("Weather API key is not configured.")
        if not city or not city.strip():
            raise ValueError("City name is required.")
        try:
            data = WeatherService._get_json("openweather", Config.WEATHER_API_URL, {"q": city.strip(), "appid": Config.WEATHER_API_KEY, "units": units}, cache_seconds=300)
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) == 401:
                raise ValueError("OpenWeather API key is invalid, inactive, or not authorized.") from exc
            if getattr(exc.response, "status_code", None) == 404:
                raise ValueError(f"Weather location '{city.strip()}' was not found.") from exc
            raise
        return WeatherService._validated_current_weather(data)

    @staticmethod
    def get_current_weather_by_coordinates(latitude: float, longitude: float, units: str = "metric") -> dict:
        if not Config.WEATHER_API_KEY:
            raise ValueError("Weather API key is not configured.")
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        try:
            data = WeatherService._get_json("openweather", Config.WEATHER_API_URL, {"lat": latitude, "lon": longitude, "appid": Config.WEATHER_API_KEY, "units": units}, cache_seconds=300)
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) == 401:
                raise ValueError("OpenWeather API key is invalid, inactive, or not authorized.") from exc
            if getattr(exc.response, "status_code", None) == 404:
                raise ValueError("Weather information for the specified location was not found.") from exc
            raise
        return WeatherService._validated_current_weather(data)

    @staticmethod
    def get_forecast_by_coordinates(latitude: float, longitude: float, forecast_days: int = 7) -> dict:
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        if forecast_days != 7:
            raise ValueError("Forecast days must be 7.")
        params = {
            "latitude": latitude, "longitude": longitude, "current": "temperature_2m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,et0_fao_evapotranspiration",
            "forecast_days": 7, "timezone": "auto",
        }
        data = WeatherService._get_json("open-meteo-forecast", "https://api.open-meteo.com/v1/forecast", params, cache_seconds=1800)
        daily = data.get("daily") or {}
        if not isinstance(daily, dict):
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["open-meteo-forecast"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("Weather provider returned an invalid forecast.")
        dates = daily.get("time") or []
        if not isinstance(dates, list) or not dates:
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["open-meteo-forecast"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("Weather provider returned no forecast days.")
        def at(field, index):
            values = daily.get(field)
            return values[index] if isinstance(values, list) and index < len(values) else None
        current = data.get("current") or {}
        if not isinstance(current, dict):
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["open-meteo-forecast"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("Weather provider returned invalid current forecast metadata.")
        return {
            "provider": "Open-Meteo", "latitude": data.get("latitude"), "longitude": data.get("longitude"),
            "timezone": data.get("timezone"), "timezone_abbreviation": data.get("timezone_abbreviation"),
            "provider_timestamp": current.get("time"),
            "days": [{"date": d, "weather_code": at("weather_code", i), "temperature_max": at("temperature_2m_max", i),
                "temperature_min": at("temperature_2m_min", i), "precipitation_mm": at("precipitation_sum", i),
                "precipitation_probability": at("precipitation_probability_max", i), "wind_speed_max": at("wind_speed_10m_max", i),
                "et0_mm": at("et0_fao_evapotranspiration", i)} for i, d in enumerate(dates[:7])],
        }

    @staticmethod
    def get_historical_water_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
        """Daily precipitation/FAO-56 ET0 from Open-Meteo reanalysis (not station measurements)."""
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        params = {
            "latitude": latitude, "longitude": longitude, "start_date": start_date, "end_date": end_date,
            "daily": "precipitation_sum,et0_fao_evapotranspiration", "timezone": "auto",
        }
        data = WeatherService._get_json("open-meteo-archive", "https://archive-api.open-meteo.com/v1/archive", params, cache_seconds=21600)
        daily = data.get("daily") or {}
        if not isinstance(daily, dict):
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["open-meteo-archive"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("Open-Meteo archive returned an invalid water-balance response.")
        dates, rain, et0 = daily.get("time") or [], daily.get("precipitation_sum"), daily.get("et0_fao_evapotranspiration")
        if not isinstance(dates, list) or not dates or not isinstance(rain, list) or not isinstance(et0, list):
            with _CACHE_LOCK:
                _UNAVAILABLE_UNTIL["open-meteo-archive"] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS
            raise requests.RequestException("Open-Meteo archive returned incomplete water-balance data.")
        return {"provider": "Open-Meteo Historical Weather API (reanalysis)", "data_type": "historical_reanalysis_not_station_measurements",
            "timezone": data.get("timezone"), "days": [{"date": day, "precipitation_mm": rain[i] if i < len(rain) else None,
            "et0_mm": et0[i] if i < len(et0) else None} for i, day in enumerate(dates)]}

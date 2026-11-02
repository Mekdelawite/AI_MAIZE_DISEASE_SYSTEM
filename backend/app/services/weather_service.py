"""Weather integrations: OpenWeather current conditions and Open-Meteo forecast/archive."""
from __future__ import annotations

from datetime import datetime, timezone
import requests
from backend.app.config import Config


class WeatherService:
    @staticmethod
    def _format_weather_response(data: dict) -> dict:
        items = data.get("weather") or [{}]
        rain = data.get("rain") or {}
        period = next((hours for hours in (1, 3) if isinstance(rain.get(f"{hours}h"), (int, float))), None)
        result = {
            "location": data.get("name"), "country": data.get("sys", {}).get("country"),
            "latitude": data.get("coord", {}).get("lat"), "longitude": data.get("coord", {}).get("lon"),
            "temperature": data.get("main", {}).get("temp"), "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"), "pressure": data.get("main", {}).get("pressure"),
            "wind_speed": data.get("wind", {}).get("speed"), "weather": items[0].get("main"),
            "description": items[0].get("description"), "icon": items[0].get("icon"),
            "timestamp": datetime.fromtimestamp(data["dt"], tz=timezone.utc).isoformat() if isinstance(data.get("dt"), (int, float)) else None,
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
        response = requests.get(Config.WEATHER_API_URL, params={"q": city.strip(), "appid": Config.WEATHER_API_KEY, "units": units}, timeout=10)
        if response.status_code == 401:
            raise ValueError("OpenWeather API key is invalid, inactive, or not authorized.")
        if response.status_code == 404:
            raise ValueError(f"Weather location '{city.strip()}' was not found.")
        response.raise_for_status()
        return WeatherService._format_weather_response(response.json())

    @staticmethod
    def get_current_weather_by_coordinates(latitude: float, longitude: float, units: str = "metric") -> dict:
        if not Config.WEATHER_API_KEY:
            raise ValueError("Weather API key is not configured.")
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        response = requests.get(Config.WEATHER_API_URL, params={"lat": latitude, "lon": longitude, "appid": Config.WEATHER_API_KEY, "units": units}, timeout=10)
        if response.status_code == 401:
            raise ValueError("OpenWeather API key is invalid, inactive, or not authorized.")
        if response.status_code == 404:
            raise ValueError("Weather information for the specified location was not found.")
        response.raise_for_status()
        return WeatherService._format_weather_response(response.json())

    @staticmethod
    def get_forecast_by_coordinates(latitude: float, longitude: float, forecast_days: int = 7) -> dict:
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        if forecast_days != 7:
            raise ValueError("Forecast days must be 7.")
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": latitude, "longitude": longitude, "current": "temperature_2m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,et0_fao_evapotranspiration",
            "forecast_days": 7, "timezone": "auto",
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            raise requests.RequestException("Weather provider returned no forecast days.")
        def at(field, index):
            values = daily.get(field)
            return values[index] if isinstance(values, list) and index < len(values) else None
        return {
            "provider": "Open-Meteo", "latitude": data.get("latitude"), "longitude": data.get("longitude"),
            "timezone": data.get("timezone"), "timezone_abbreviation": data.get("timezone_abbreviation"),
            "provider_timestamp": (data.get("current") or {}).get("time"),
            "days": [{"date": d, "weather_code": at("weather_code", i), "temperature_max": at("temperature_2m_max", i),
                "temperature_min": at("temperature_2m_min", i), "precipitation_mm": at("precipitation_sum", i),
                "precipitation_probability": at("precipitation_probability_max", i), "wind_speed_max": at("wind_speed_10m_max", i),
                "et0_mm": at("et0_fao_evapotranspiration", i)} for i, d in enumerate(dates[:7])],
        }

    @staticmethod
    def get_historical_water_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
        """Daily precipitation/FAO-56 ET0 from Open-Meteo reanalysis (not station measurements)."""
        latitude, longitude = WeatherService._coordinates(latitude, longitude)
        response = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
            "latitude": latitude, "longitude": longitude, "start_date": start_date, "end_date": end_date,
            "daily": "precipitation_sum,et0_fao_evapotranspiration", "timezone": "auto",
        }, timeout=15)
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily") or {}
        dates, rain, et0 = daily.get("time") or [], daily.get("precipitation_sum"), daily.get("et0_fao_evapotranspiration")
        if not dates or not isinstance(rain, list) or not isinstance(et0, list):
            raise requests.RequestException("Open-Meteo archive returned incomplete water-balance data.")
        return {"provider": "Open-Meteo Historical Weather API (reanalysis)", "data_type": "historical_reanalysis_not_station_measurements",
            "timezone": data.get("timezone"), "days": [{"date": day, "precipitation_mm": rain[i] if i < len(rain) else None,
            "et0_mm": et0[i] if i < len(et0) else None} for i, day in enumerate(dates)]}

"""
=========================================================
Weather Service
=========================================================

Handles communication with the OpenWeather API for the
AI Maize Disease Detection System.

Supported weather lookups:
    - City-based weather
    - Latitude/longitude-based weather

The service layer keeps external API communication out
of the Flask routes.
=========================================================
"""

from __future__ import annotations

import requests

from backend.app.config import Config


class WeatherService:
    """
    Service responsible for retrieving weather information
    from OpenWeather.
    """

    # =====================================================
    # INTERNAL RESPONSE FORMATTER
    # =====================================================

    @staticmethod
    def _format_weather_response(data: dict) -> dict:
        """
        Convert an OpenWeather response into the application's
        standard weather response format.
        """

        weather_items = data.get("weather") or [{}]

        return {
            "location": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "latitude": (
                data.get("coord", {}).get("lat")
            ),
            "longitude": (
                data.get("coord", {}).get("lon")
            ),
            "temperature": (
                data.get("main", {}).get("temp")
            ),
            "feels_like": (
                data.get("main", {}).get("feels_like")
            ),
            "humidity": (
                data.get("main", {}).get("humidity")
            ),
            "pressure": (
                data.get("main", {}).get("pressure")
            ),
            "wind_speed": (
                data.get("wind", {}).get("speed")
            ),
            "weather": weather_items[0].get("main"),
            "description": weather_items[0].get(
                "description"
            ),
            "icon": weather_items[0].get("icon"),
        }

    # =====================================================
    # CITY WEATHER
    # =====================================================

    @staticmethod
    def get_current_weather(
        city: str,
        units: str = "metric",
    ) -> dict:
        """
        Get current weather information for a city.

        Args:
            city:
                City name, for example "Bahir Dar".

            units:
                OpenWeather measurement system.
                "metric" returns Celsius and m/s.

        Returns:
            Dictionary containing weather information.

        Raises:
            ValueError:
                If the API key is not configured or the city
                is empty/not found.

            requests.RequestException:
                If communication with OpenWeather fails.
        """

        if not Config.WEATHER_API_KEY:
            raise ValueError(
                "Weather API key is not configured."
            )

        if not city or not city.strip():
            raise ValueError(
                "City name is required."
            )

        params = {
            "q": city.strip(),
            "appid": Config.WEATHER_API_KEY,
            "units": units,
        }

        response = requests.get(
            Config.WEATHER_API_URL,
            params=params,
            timeout=10,
        )

        if response.status_code == 401:
            raise ValueError(
                "OpenWeather API key is invalid, inactive, "
                "or not authorized."
            )

        if response.status_code == 404:
            raise ValueError(
                f"Weather location '{city.strip()}' was not found."
            )

        response.raise_for_status()

        data = response.json()

        return WeatherService._format_weather_response(
            data
        )

    # =====================================================
    # COORDINATE-BASED WEATHER
    # =====================================================

    @staticmethod
    def get_current_weather_by_coordinates(
        latitude: float,
        longitude: float,
        units: str = "metric",
    ) -> dict:
        """
        Get current weather information using geographic
        coordinates.

        Args:
            latitude:
                Latitude between -90 and 90.

            longitude:
                Longitude between -180 and 180.

            units:
                OpenWeather measurement system.

        Returns:
            Dictionary containing weather information.

        Raises:
            ValueError:
                If the API key or coordinates are invalid.

            requests.RequestException:
                If communication with OpenWeather fails.
        """

        if not Config.WEATHER_API_KEY:
            raise ValueError(
                "Weather API key is not configured."
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise ValueError(
                "Latitude and longitude must be valid numbers."
            )

        if not -90 <= latitude <= 90:
            raise ValueError(
                "Latitude must be between -90 and 90."
            )

        if not -180 <= longitude <= 180:
            raise ValueError(
                "Longitude must be between -180 and 180."
            )

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": Config.WEATHER_API_KEY,
            "units": units,
        }

        response = requests.get(
            Config.WEATHER_API_URL,
            params=params,
            timeout=10,
        )

        if response.status_code == 401:
            raise ValueError(
                "OpenWeather API key is invalid, inactive, "
                "or not authorized."
            )

        if response.status_code == 404:
            raise ValueError(
                "Weather information for the specified "
                "location was not found."
            )

        response.raise_for_status()

        data = response.json()

        return WeatherService._format_weather_response(
            data
        )
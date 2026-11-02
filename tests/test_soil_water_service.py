from datetime import date
from types import SimpleNamespace

from backend.app.services.soil_water_service import SoilWaterService


def profile(**overrides):
    values = {
        "planting_date": date(2026, 6, 1),
        "soil_type": "loam",
        "available_water_capacity_mm_per_m": 140,
        "crop_growth_stage": "mid_season",
        "irrigation_status": "rainfed",
        "last_irrigation_date": None,
        "last_irrigation_mm": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def weather(days):
    return {"provider": "Open-Meteo Historical Weather API (reanalysis)", "days": days}


def test_soil_water_estimate_uses_fao56_kc_and_labels_reanalysis():
    data = weather([
        {"date": "2026-06-01", "precipitation_mm": 8, "et0_mm": 4},
        {"date": "2026-06-02", "precipitation_mm": 2, "et0_mm": 5},
    ])
    result = SoilWaterService.calculate(profile(), data, {"provider": "Open-Meteo", "days": []})
    assert result["label"] == "estimated_soil_water_not_sensor_measurement"
    assert result["historical"]["data_type"] == "reanalysis_not_station_measurements"
    assert result["historical"]["rainfall_mm"] == 10
    assert result["historical"]["etc_mm"] == 10.3
    assert result["root_zone"]["available_water_mm"] > 0


def test_missing_rainfall_or_et0_does_not_create_zero_balance():
    result = SoilWaterService.calculate(profile(), weather([
        {"date": "2026-06-01", "precipitation_mm": None, "et0_mm": 4},
    ]), None)
    assert result["historical"]["net_water_balance_mm"] is None
    assert result["root_zone"] is None
    assert result["weather_dryness_signal"] == "unavailable"


def test_missing_soil_capacity_and_planting_date_keeps_weather_signal_only():
    data = weather([{"date": "2026-06-01", "precipitation_mm": 0, "et0_mm": 5}])
    result = SoilWaterService.calculate(profile(available_water_capacity_mm_per_m=None, planting_date=None), data, None)
    assert result["root_zone"] is None
    assert result["weather_dryness_signal"] == "net_deficit"
    assert "planting_date" in result["missing_inputs"]
    assert "awc" in result["missing_inputs"]


def test_growth_stage_changes_crop_et_estimate_and_stale_data_reduces_reliability():
    data = weather([{"date": "2026-10-20", "precipitation_mm": 0, "et0_mm": 5}])
    mid = SoilWaterService.calculate(profile(), data, None)
    initial = SoilWaterService.calculate(profile(crop_growth_stage="initial"), data, None)
    assert mid["historical"]["etc_mm"] > initial["historical"]["etc_mm"]
    assert mid["historical"]["stale"] is True
    assert mid["reliability"] == "low"


def test_forecast_balance_is_separate_from_historical_balance():
    historical = weather([{"date": "2026-10-30", "precipitation_mm": 2, "et0_mm": 5}])
    forecast = {"provider": "Open-Meteo", "days": [{"precipitation_mm": 6, "et0_mm": 3}]}
    result = SoilWaterService.calculate(profile(), historical, forecast)
    assert result["historical"]["net_water_balance_mm"] == -3.8
    assert result["forecast"]["net_water_balance_mm"] == 2.6

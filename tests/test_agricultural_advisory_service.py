from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.services.agricultural_advisory_service import AgriculturalAdvisoryService


def _profile(stage=None, planting_date=date(2026, 4, 20), soil_type="loam", awc=140):
    return SimpleNamespace(
        crop_growth_stage=stage,
        planting_date=planting_date,
        soil_type=soil_type,
        available_water_capacity_mm_per_m=awc,
    )


def _calendar(month=8):
    if month in (3,):
        stage = "land_preparation"
    elif month in (4, 5):
        stage = "planting"
    elif month == 6:
        stage = "early_growth"
    elif month in (7, 8):
        stage = "mid_season"
    elif month >= 9:
        stage = "harvest"
    else:
        stage = "off_season"
    return {"reference_date": date(2026, month, 1).isoformat(), "current_stage": {"stage": stage}}


def _soil(balance=None, stale=False):
    return {
        "historical": {"net_water_balance_mm": balance, "stale": stale},
        "reliability": "moderate",
    }


def _get_stage_key(result):
    return result["stage"]["stage_key"]


def test_farmer_confirmed_stage_is_respected():
    result = AgriculturalAdvisoryService.generate(
        profile=_profile("initial"), calendar=_calendar(8), current_weather=None,
        forecast=None, soil_water=_soil(), historical=None,
    )

    assert _get_stage_key(result) == "advisoryStageSeedling"
    assert result["stage"]["basis"] == "farmer_confirmed"
    assert result["recommendations"][0]["stage_basis"] == "farmer_confirmed"


def test_calendar_stage_is_estimated_and_missing_planting_date_is_explained():
    result = AgriculturalAdvisoryService.generate(
        profile=_profile(None, planting_date=None, soil_type=None, awc=None), calendar=_calendar(8), current_weather=None,
        forecast=None, soil_water=_soil(), historical=None,
    )

    assert _get_stage_key(result) == "advisoryStageFlowering"
    assert result["stage"]["basis"] == "calendar_estimate"
    assert "advisoryMissingPlantingDate" in result["missing_data_keys"]
    assert "advisoryMissingForecast" in result["missing_data_keys"]
    assert {item["category"] for item in result["recommendations"]} == {"crop_stage"}


def test_weather_and_dryness_recommendations_require_real_provider_signals():
    profile = _profile(None, soil_type=None, awc=None)
    forecast = {"days": [
        {"date": "2026-08-02", "weather_code": 65, "precipitation_mm": 18},
        {"date": "2026-08-03", "weather_code": 0, "precipitation_mm": 0},
    ]}
    result = AgriculturalAdvisoryService.generate(
        profile=profile, calendar=_calendar(8), current_weather={"temperature": 31, "humidity": 25},
        forecast=forecast, soil_water=_soil(balance=-12, stale=False),
        historical={"days": [{"date": "2026-08-01"}]},
    )

    by_id = {item["id"]: item for item in result["recommendations"]}
    assert "forecast_heavy_rain" in by_id
    assert "dryness_risk" in by_id
    assert "flowering_heat_watch" in by_id
    assert by_id["forecast_heavy_rain"]["sources"][0]["key"] == "advisorySourceForecast"
    assert by_id["dryness_risk"]["reliability"] in {"low", "moderate"}
    assert "advisoryMissingSoilType" in result["missing_data_keys"]
    assert "advisoryMissingWaterCapacity" in result["missing_data_keys"]


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (3, "advisoryStagePlanting"),
        (6, "advisoryStageSeedling"),
        (7, "advisoryStageVegetative"),
        (8, "advisoryStageFlowering"),
        (9, "advisoryStageGrain"),
        (11, "advisoryStageHarvest"),
    ],
)
def test_calendar_estimate_covers_maize_growth_phases(month, expected):
    result = AgriculturalAdvisoryService.generate(
        profile=_profile(None), calendar=_calendar(month), current_weather=None,
        forecast=None, soil_water=_soil(), historical=None,
    )
    assert _get_stage_key(result) == expected


def test_forecast_heavy_rain_generates_precaution_without_claiming_damage():
    result = AgriculturalAdvisoryService.generate(
        profile=_profile("development"), calendar=_calendar(7), current_weather=None,
        forecast={"days": [{"weather_code": 82, "precipitation_mm": 18.5}]},
        soil_water=_soil(), historical=None,
    )

    rain_advice = next(item for item in result["recommendations"] if item["id"] == "forecast_heavy_rain")
    assert rain_advice["priority"] == "medium"
    assert rain_advice["supporting_data"][0]["value"] == 18.5
    assert rain_advice["sources"][0]["key"] == "advisorySourceForecast"


def test_dryness_advice_requires_fresh_negative_historical_balance():
    result = AgriculturalAdvisoryService.generate(
        profile=_profile("mid_season"), calendar=_calendar(7), current_weather=None,
        forecast={"days": [{"precipitation_mm": 0}]},
        soil_water=_soil(-24.2, stale=False), historical={"days": [{"date": "2026-10-31"}]},
    )
    dryness = next(item for item in result["recommendations"] if item["id"] == "dryness_risk")
    assert dryness["priority"] == "high"
    assert dryness["supporting_data"][0]["value"] == -24.2

    stale_result = AgriculturalAdvisoryService.generate(
        profile=_profile("mid_season"), calendar=_calendar(7), current_weather=None,
        forecast=None, soil_water=_soil(-24.2, stale=True), historical={"days": [{"date": "2026-01-01"}]},
    )
    assert all(item["id"] != "dryness_risk" for item in stale_result["recommendations"])


def test_heat_watch_requires_flowering_stage_and_matching_current_observations():
    result = AgriculturalAdvisoryService.generate(
        profile=_profile(None), calendar=_calendar(8),
        current_weather={"temperature": 31, "humidity": 25}, forecast=None,
        soil_water=_soil(), historical=None,
    )
    assert any(item["id"] == "flowering_heat_watch" for item in result["recommendations"])

    non_flowering = AgriculturalAdvisoryService.generate(
        profile=_profile("development"), calendar=_calendar(7),
        current_weather={"temperature": 35, "humidity": 20}, forecast=None,
        soil_water=_soil(), historical=None,
    )
    assert all(item["id"] != "flowering_heat_watch" for item in non_flowering["recommendations"])

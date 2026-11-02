"""Rule-based, explainable maize advisories built from existing farm data.

Calendar timing is an estimate, not a field observation. Weather-triggered rules
use provider conditions/codes and Phase 3's explicit water-balance signal; this
service does not infer fertilizer, pesticide, or yield recommendations.
"""
from __future__ import annotations

from datetime import date
from typing import Any


class AgriculturalAdvisoryService:
    SOURCES = {
        "ethiopian_maize_manual": {
            "key": "advisorySourceEthiopianMoa",
            "url": "https://www.moa.gov.et/wp-content/uploads/2024/11/202112_Maize-compressed-1.pdf",
        },
        "ethiopian_irrigation_agronomy": {
            "key": "advisorySourceEthiopianIrrigation",
            "url": "https://www.moa.gov.et/wp-content/uploads/2024/11/201109_Guideline-on-Irrigation-Agronomy-compressed.pdf",
        },
        "fao_crop_water": {
            "key": "advisorySourceFaoCropWater",
            "url": "https://www.fao.org/4/s8376e/s8376e.pdf",
        },
        "open_meteo_forecast": {
            "key": "advisorySourceForecast",
            "url": "https://open-meteo.com/en/docs",
        },
        "open_meteo_reanalysis": {
            "key": "advisorySourceReanalysis",
            "url": "https://open-meteo.com/en/docs/historical-weather-api",
        },
        "open_weather_current": {
            "key": "advisorySourceCurrentWeather",
            "url": "https://openweathermap.org/current",
        },
    }

    CONFIRMED_STAGE = {
        "initial": "germination_seedling",
        "development": "vegetative_growth",
        # The saved profile value is intentionally kept broad; it does not
        # assert that tassels or silks have been observed.
        "mid_season": "farmer_confirmed_mid_season",
        "late_season": "grain_development_maturity",
    }

    STAGE_ADVICE = {
        "land_preparation_planting": {
            "title": "advisoryStagePlantingTitle", "explanation": "advisoryStagePlantingExplanation",
            "action": "advisoryStagePlantingAction", "reason": "advisoryStagePlantingReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingBeforePlanting",
        },
        "germination_seedling": {
            "title": "advisoryStageSeedlingTitle", "explanation": "advisoryStageSeedlingExplanation",
            "action": "advisoryStageSeedlingAction", "reason": "advisoryStageSeedlingReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingNow",
        },
        "vegetative_growth": {
            "title": "advisoryStageVegetativeTitle", "explanation": "advisoryStageVegetativeExplanation",
            "action": "advisoryStageVegetativeAction", "reason": "advisoryStageVegetativeReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingNow",
        },
        "flowering_pollination": {
            "title": "advisoryStageFloweringTitle", "explanation": "advisoryStageFloweringExplanation",
            "action": "advisoryStageFloweringAction", "reason": "advisoryStageFloweringReason",
            "source_ids": ("fao_crop_water", "ethiopian_irrigation_agronomy"), "timing": "advisoryTimingNow",
        },
        "grain_development_maturity": {
            "title": "advisoryStageGrainTitle", "explanation": "advisoryStageGrainExplanation",
            "action": "advisoryStageGrainAction", "reason": "advisoryStageGrainReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingNow",
        },
        "harvest_post_harvest": {
            "title": "advisoryStageHarvestTitle", "explanation": "advisoryStageHarvestExplanation",
            "action": "advisoryStageHarvestAction", "reason": "advisoryStageHarvestReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingAtMaturity",
        },
        "farmer_confirmed_mid_season": {
            "title": "advisoryStageMidSeasonTitle", "explanation": "advisoryStageMidSeasonExplanation",
            "action": "advisoryStageMidSeasonAction", "reason": "advisoryStageMidSeasonReason",
            "source_ids": ("ethiopian_maize_manual",), "timing": "advisoryTimingNow",
        },
    }

    @staticmethod
    def _valid_nonnegative(value: Any) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value) if value >= 0 else None

    @classmethod
    def _calendar_stage(cls, calendar: dict, profile) -> str:
        planting_date = getattr(profile, "planting_date", None)
        if isinstance(planting_date, date) and planting_date > date.today():
            return "land_preparation_planting"
        try:
            month = date.fromisoformat(calendar["reference_date"]).month
        except (KeyError, TypeError, ValueError):
            month = date.today().month
        existing_stage = (calendar.get("current_stage") or {}).get("stage")
        if existing_stage in {"land_preparation", "planting"}:
            return "land_preparation_planting"
        if existing_stage == "early_growth":
            return "germination_seedling"
        if existing_stage == "mid_season":
            # The existing calendar has a broad mid-season interval. Split its
            # early and late months only for a coarse, clearly labelled estimate.
            return "vegetative_growth" if month == 7 else "flowering_pollination"
        if existing_stage == "harvest":
            return "grain_development_maturity" if month <= 10 else "harvest_post_harvest"
        return "land_preparation_planting"

    @staticmethod
    def _stage_label_key(stage: str) -> str:
        return {
            "land_preparation_planting": "advisoryStagePlanting",
            "germination_seedling": "advisoryStageSeedling",
            "vegetative_growth": "advisoryStageVegetative",
            "flowering_pollination": "advisoryStageFlowering",
            "grain_development_maturity": "advisoryStageGrain",
            "harvest_post_harvest": "advisoryStageHarvest",
            "farmer_confirmed_mid_season": "advisoryStageMidSeason",
        }.get(stage, "advisoryStageUnknown")

    @classmethod
    def _recommendation(
        cls, *, identifier: str, category: str, stage: str, basis: str,
        content: dict, priority: str, sources: tuple[str, ...], timing: str,
        reliability: str, supporting_data: list[dict] | None = None,
    ) -> dict:
        return {
            "id": identifier,
            "category": category,
            "title_key": content["title"],
            "explanation_key": content["explanation"],
            "action_key": content["action"],
            "reason_key": content["reason"],
            "stage_key": cls._stage_label_key(stage),
            "stage_basis": basis,
            "priority": priority,
            "priority_key": f"advisoryPriority{priority.title()}",
            "timing_key": timing,
            "source_ids": list(sources),
            "sources": [cls.SOURCES[source_id] for source_id in sources],
            "reliability": reliability,
            "reliability_key": f"advisoryReliability{reliability.title()}",
            "supporting_data": supporting_data or [],
        }

    @classmethod
    def generate(
        cls, *, profile, calendar: dict, current_weather: dict | None,
        forecast: dict | None, soil_water: dict, historical: dict | None,
    ) -> dict:
        """Build a small set of deduplicated, evidence-linked recommendations."""
        calendar_stage = cls._calendar_stage(calendar, profile)
        confirmed_value = getattr(profile, "crop_growth_stage", None)
        confirmed_stage = cls.CONFIRMED_STAGE.get(confirmed_value)
        stage = confirmed_stage or calendar_stage
        basis = "farmer_confirmed" if confirmed_stage else "calendar_estimate"
        planting_date = getattr(profile, "planting_date", None)
        missing = []
        if planting_date is None:
            missing.append("advisoryMissingPlantingDate")
        if not confirmed_stage:
            missing.append("advisoryMissingConfirmedStage")
        if current_weather is None:
            missing.append("advisoryMissingCurrentWeather")
        if not forecast or not forecast.get("days"):
            missing.append("advisoryMissingForecast")
        if not historical or not (historical.get("days") or []):
            missing.append("advisoryMissingHistoricalWeather")
        if not getattr(profile, "soil_type", None):
            missing.append("advisoryMissingSoilType")
        if getattr(profile, "available_water_capacity_mm_per_m", None) is None:
            missing.append("advisoryMissingWaterCapacity")

        items = []
        stage_content = cls.STAGE_ADVICE[stage]
        stage_reliability = "moderate" if basis == "farmer_confirmed" else "low"
        items.append(cls._recommendation(
            identifier="crop_stage", category="crop_stage", stage=stage, basis=basis,
            content=stage_content, priority="routine", sources=stage_content["source_ids"],
            timing=stage_content["timing"], reliability=stage_reliability,
        ))

        if confirmed_stage and confirmed_stage != calendar_stage:
            stage_comparison = {
                "confirmed_stage_key": cls._stage_label_key(confirmed_stage),
                "calendar_stage_key": cls._stage_label_key(calendar_stage),
                "explanation_key": "advisoryStageDifference",
            }
        else:
            stage_comparison = None

        forecast_days = (forecast or {}).get("days") or []
        heavy_rain_days = [
            day for day in forecast_days
            if day.get("weather_code") in (65, 66, 67, 82, 95, 96, 99)
        ]
        if heavy_rain_days:
            rain_values = [self_value for day in heavy_rain_days
                           if (self_value := cls._valid_nonnegative(day.get("precipitation_mm"))) is not None]
            support = []
            if rain_values:
                support.append({"label_key": "advisoryDataForecastRain", "value": round(sum(rain_values), 1), "unit": "mm",
                                "source_id": "open_meteo_forecast"})
            items.append(cls._recommendation(
                identifier="forecast_heavy_rain", category="weather", stage=stage, basis=basis,
                content={"title": "advisoryHeavyRainTitle", "explanation": "advisoryHeavyRainExplanation",
                         "action": "advisoryHeavyRainAction", "reason": "advisoryHeavyRainReason"},
                priority="medium", sources=("open_meteo_forecast",), timing="advisoryTimingNextSevenDays",
                reliability="moderate", supporting_data=support,
            ))

        historical_balance = (soil_water or {}).get("historical", {}).get("net_water_balance_mm")
        history_stale = (soil_water or {}).get("historical", {}).get("stale", True)
        forecast_rain = [cls._valid_nonnegative(day.get("precipitation_mm")) for day in forecast_days]
        forecast_is_dry = bool(forecast_days) and all(value == 0 for value in forecast_rain)
        if historical_balance is not None and historical_balance < 0 and not history_stale:
            support = [{"label_key": "advisoryDataHistoricalBalance", "value": historical_balance, "unit": "mm",
                        "source_id": "open_meteo_reanalysis"}]
            if forecast_is_dry:
                support.append({"label_key": "advisoryDataForecastRain", "value": 0, "unit": "mm",
                                "source_id": "open_meteo_forecast"})
            flowering_sensitive = stage in {"flowering_pollination", "farmer_confirmed_mid_season"}
            items.append(cls._recommendation(
                identifier="dryness_risk", category="soil_water", stage=stage, basis=basis,
                content={"title": "advisoryDrynessTitle", "explanation": "advisoryDrynessExplanation",
                         "action": "advisoryDrynessAction", "reason": "advisoryDrynessReason"},
                priority="high" if flowering_sensitive else "medium",
                sources=("open_meteo_reanalysis", "fao_crop_water", "ethiopian_maize_manual"),
                timing="advisoryTimingNow", reliability="low" if soil_water.get("reliability") == "low" else "moderate",
                supporting_data=support,
            ))

        current_temp = cls._valid_nonnegative((current_weather or {}).get("temperature"))
        current_humidity = cls._valid_nonnegative((current_weather or {}).get("humidity"))
        # Ethiopian MoA irrigation-agronomy material describes impaired maize
        # pollination at >30–35 C under about 30% RH. Use the low end only as a
        # conservative watch signal when both live values and reproductive-stage
        # context exist; this is not a crop-damage prediction.
        if (stage == "flowering_pollination" and current_temp is not None and current_temp > 30
                and current_humidity is not None and current_humidity <= 30):
            items.append(cls._recommendation(
                identifier="flowering_heat_watch", category="weather", stage=stage, basis=basis,
                content={"title": "advisoryHeatTitle", "explanation": "advisoryHeatExplanation",
                         "action": "advisoryHeatAction", "reason": "advisoryHeatReason"},
                priority="medium", sources=("ethiopian_irrigation_agronomy", "open_weather_current"),
                timing="advisoryTimingNow", reliability="low",
                supporting_data=[
                    {"label_key": "advisoryDataCurrentTemperature", "value": current_temp, "unit": "°C", "source_id": "open_weather_current"},
                    {"label_key": "advisoryDataCurrentHumidity", "value": current_humidity, "unit": "%", "source_id": "open_weather_current"},
                ],
            ))

        # Distinct rules may refer to the same source category, but never emit
        # duplicate cards for the same recommendation identifier.
        unique_items = list({item["id"]: item for item in items}.values())
        return {
            "recommendations": unique_items,
            "stage": {
                "stage_key": cls._stage_label_key(stage),
                "basis": basis,
                "planting_date": planting_date.isoformat() if isinstance(planting_date, date) else None,
                "calendar_stage_key": cls._stage_label_key(calendar_stage),
                "comparison": stage_comparison,
            },
            "missing_data_keys": missing,
            "disclaimer_key": "advisoryProfessionalDisclaimer",
            "method_key": "advisoryMethodNote",
        }

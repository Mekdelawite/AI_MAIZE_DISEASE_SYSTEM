"""FAO-56-inspired daily root-zone depletion balance with explicit assumptions."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


class SoilWaterService:
    # FAO-56 single crop coefficient values for grain maize, representative stage values.
    KC = {"initial": 0.40, "development": 0.80, "mid_season": 1.15, "late_season": 0.70}
    ROOT_DEPTH_M = {"initial": 0.30, "development": 0.60, "mid_season": 1.00, "late_season": 1.00}

    @classmethod
    def calculate(cls, profile, historical: dict | None, forecast: dict | None) -> dict:
        now = datetime.now(timezone.utc)
        days = (historical or {}).get("days", [])
        forecast_days = (forecast or {}).get("days", [])
        missing = []
        for field, label in (("planting_date", "planting_date"), ("crop_growth_stage", "growth_stage"),
                             ("available_water_capacity_mm_per_m", "awc")):
            if getattr(profile, field, None) is None:
                missing.append(label)
        if not days:
            missing.append("historical_weather")
        if (historical or {}).get("window_truncated"):
            missing.append("history_window")

        def num(value):
            return float(value) if isinstance(value, (int, float)) and value >= 0 else None

        valid_hist = [d for d in days if num(d.get("precipitation_mm")) is not None and num(d.get("et0_mm")) is not None]
        weather_complete = bool(days) and len(valid_hist) == len(days)
        if days and not weather_complete:
            missing.append("complete_weather")
        hist_rain = sum(num(d.get("precipitation_mm")) or 0 for d in valid_hist)
        hist_et0 = sum(num(d.get("et0_mm")) or 0 for d in valid_hist)
        stage = getattr(profile, "crop_growth_stage", None)
        kc = cls.KC.get(stage)
        etc = hist_et0 * kc if kc is not None and weather_complete else None
        irrigation_mm = 0.0
        irrigation_date = getattr(profile, "last_irrigation_date", None)
        irrigation_depth = getattr(profile, "last_irrigation_mm", None)
        if irrigation_date and irrigation_depth is not None and (not days or (days[0]["date"] <= irrigation_date.isoformat() <= days[-1]["date"])):
            irrigation_mm = float(irrigation_depth)
        if getattr(profile, "irrigation_status", None) == "irrigated" and (irrigation_depth is None or irrigation_date is None):
            missing.append("irrigation_event")
        effective_rain = hist_rain  # simplified: no runoff/interception data; all reanalysis rain is provisionally available.
        balance = effective_rain + irrigation_mm - etc if etc is not None else None
        awc = getattr(profile, "available_water_capacity_mm_per_m", None)
        root_depth = cls.ROOT_DEPTH_M.get(stage)
        root_estimate = None
        if not missing and balance is not None and awc is not None and root_depth:
            taw = float(awc) * root_depth
            # Starting storage at field capacity on planting date is an unverified model initialization.
            deficit = min(taw, max(0.0, -balance))
            root_estimate = {"available_water_mm": round(taw - deficit, 1), "total_available_water_mm": round(taw, 1),
                "depletion_mm": round(deficit, 1), "unit": "mm", "initialization": "assumed_field_capacity_at_planting"}

        future_rain = [num(d.get("precipitation_mm")) for d in forecast_days]
        future_et0 = [num(d.get("et0_mm")) for d in forecast_days]
        forecast_complete = bool(forecast_days) and all(v is not None for v in future_rain + future_et0)
        forecast_balance = None
        if forecast_complete and kc is not None:
            forecast_balance = round(sum(future_rain) - sum(future_et0) * kc, 1)

        latest = max((d.get("date") for d in valid_hist if d.get("date")), default=None)
        stale = True
        if latest:
            try:
                stale = (date.today() - date.fromisoformat(latest)).days > 3
            except ValueError:
                pass

        return {
            "label": "estimated_soil_water_not_sensor_measurement",
            "calculated_at": now.isoformat(),
            "historical": {"source": (historical or {}).get("provider"), "data_type": "reanalysis_not_station_measurements",
                "start_date": days[0].get("date") if days else None, "end_date": latest,
                "rainfall_mm": round(hist_rain, 1) if valid_hist else None,
                "et0_mm": round(hist_et0, 1) if weather_complete else None,
                "etc_mm": round(etc, 1) if etc is not None else None,
                "irrigation_mm": round(irrigation_mm, 1) if irrigation_mm else None,
                "net_water_balance_mm": round(balance, 1) if balance is not None else None,
                "latest_data_date": latest, "stale": stale},
            "forecast": {"source": (forecast or {}).get("provider"), "days": len(forecast_days),
                "rainfall_mm": round(sum(future_rain), 1) if forecast_complete else None,
                "et0_mm": round(sum(future_et0), 1) if forecast_complete else None,
                "net_water_balance_mm": forecast_balance},
            "crop_growth_stage": stage, "soil_type": getattr(profile, "soil_type", None),
            "irrigation_status": getattr(profile, "irrigation_status", None), "root_zone": root_estimate,
            "weather_dryness_signal": ("net_deficit" if balance is not None and balance < 0 else "net_surplus" if balance is not None else "unavailable"),
            "missing_inputs": missing,
            "reliability": "low" if stale or missing or getattr(profile, "irrigation_status", None) in (None, "unknown") else "moderate",
            "assumptions": ["reanalysis", "kc_stage", "initial_storage", "rainfall_effective", "irrigation_unreported"],
            "recommendation": ("monitor_dryness" if balance is not None and balance < 0 else
                "monitor_drainage" if balance is not None and balance > 0 else "field_observation"),
        }

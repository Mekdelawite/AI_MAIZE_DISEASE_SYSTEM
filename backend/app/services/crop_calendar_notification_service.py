"""Idempotent scheduled crop reminders and evidence-based weather alerts.

Activity timing reuses the existing farmer planting date. The 25-day weed-check
window follows Ethiopia's MoA maize production guide; it is a field inspection
reminder, not a fertilizer or pesticide prescription. Weather alerts are only
created from current provider data and Phase 4's existing advisory rules.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, time as local_time
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models import FarmerNotification, FarmerProfile, User
from backend.app.services.agricultural_advisory_service import AgriculturalAdvisoryService
from backend.app.services.crop_calendar_service import CropCalendarService
from backend.app.services.soil_water_service import SoilWaterService
from backend.app.services.sms_service import SMSService
from backend.app.services.weather_service import WeatherService


class CropCalendarNotificationService:
    CATEGORY_MAP = {"crop_activity": "crop_activity", "weather_alert": "weather_alert", "soil_water_alert": "soil_water_alert", "agricultural_advisory": "agricultural_advisory", "outbreak_alert": "important_alerts", "regional_alert": "important_alerts"}

    @staticmethod
    def preferences(profile):
        defaults = {key: {"in_app": True, "sms": True} for key in ("crop_activity", "weather_alert", "soil_water_alert", "agricultural_advisory", "important_alerts")}
        saved = getattr(profile, "notification_preferences", None) or {}
        if not isinstance(saved, dict):
            saved = {}
        categories = {}
        raw_categories = saved.get("categories") if isinstance(saved.get("categories"), dict) else {}
        for key, channels in defaults.items():
            raw = raw_categories.get(key) if isinstance(raw_categories.get(key), dict) else {}
            categories[key] = {channel: raw.get(channel) if isinstance(raw.get(channel), bool) else enabled for channel, enabled in channels.items()}
        quiet = saved.get("quiet_hours") if isinstance(saved.get("quiet_hours"), dict) else {}
        start, end = quiet.get("start", "21:00"), quiet.get("end", "07:00")
        try:
            local_time.fromisoformat(start)
            local_time.fromisoformat(end)
            valid_times = True
        except (TypeError, ValueError):
            valid_times = False
        if not valid_times or not isinstance(quiet.get("enabled", False), bool):
            quiet = {"enabled": False, "start": "21:00", "end": "07:00"}
        try:
            reminder_days = int(saved.get("reminder_days_before", 0))
            if reminder_days not in (0, 1, 2, 3):
                reminder_days = 0
        except (TypeError, ValueError):
            reminder_days = 0
        timezone_name = saved.get("timezone") or "Africa/Addis_Ababa"
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(timezone_name)
        except (TypeError, ValueError, KeyError):
            timezone_name = "Africa/Addis_Ababa"
        return {**saved, "categories": categories, "quiet_hours": {"enabled": quiet.get("enabled", False), "start": start, "end": end}, "reminder_days_before": reminder_days, "timezone": timezone_name}

    @classmethod
    def quiet_now(cls, profile, *, now=None, critical=False):
        # Critical alerts may bypass quiet hours (configurable), never explicit category/SMS opt-outs.
        from flask import current_app, has_app_context
        if critical and has_app_context() and current_app.config.get("CRITICAL_ALERTS_BYPASS_QUIET_HOURS", True):
            return False
        prefs = cls.preferences(profile)
        quiet = prefs["quiet_hours"]
        if not quiet["enabled"]:
            return False
        from zoneinfo import ZoneInfo
        local = (now or datetime.now(ZoneInfo(prefs["timezone"]))).astimezone(ZoneInfo(prefs["timezone"]))
        start, end = (local_time.fromisoformat(quiet[k]) for k in ("start", "end"))
        current = local.timetz().replace(tzinfo=None)
        if start == end:
            return False
        return (start <= current < end) if start < end else (current >= start or current < end)

    @classmethod
    def local_today(cls, profile=None) -> date:
        timezone_name = cls.preferences(profile)["timezone"] if profile is not None else "Africa/Addis_Ababa"
        return datetime.now(ZoneInfo(timezone_name)).date()

    REMINDERS = {
        "land_preparation": {
            "title": ("Prepare the field for planting", "ለመዝራት መሬቱን ያዘጋጁ"),
            "message": (
                "Your recorded maize planting date is approaching. Prepare the seedbed and check local rainfall and soil moisture with your extension worker before planting.",
                "ያስቀመጡት የበቆሎ መዝሪያ ቀን እየቀረበ ነው። ከመዝራትዎ በፊት የዘር መደቡን ያዘጋጁ፤ የአካባቢ ዝናብንና የአፈር እርጥበትን ከግብርና ባለሙያ ጋር ያረጋግጡ።",
            ),
        },
        "planting": {
            "title": ("Maize planting reminder", "የበቆሎ መዝራት ማስታወሻ"),
            "message": (
                "Your saved planting date is near. Plant only when adequate local soil moisture and the onset of rain are confirmed. Review the locally recommended nutrient plan with your extension worker; this reminder does not prescribe rates.",
                "ያስቀመጡት የመዝሪያ ቀን ቀርቧል። በአካባቢው በቂ የአፈር እርጥበትና የዝናብ መጀመር ሲረጋገጥ ብቻ ይዝሩ። በአካባቢው የሚመከረውን የማዳበሪያ እቅድ ከግብርና ባለሙያዎ ጋር ይከልሱ፤ ይህ ማስታወሻ መጠን አይመክርም።",
            ),
        },
        "weed_inspection": {
            "title": ("Check early weed pressure", "የአረም ሁኔታን ይፈትሹ"),
            "message": (
                "About 25–30 days after your recorded planting date, inspect the maize for weed competition, crop establishment, and visible pest or disease symptoms. Adapt any control action to local extension advice.",
                "ከተመዘገበው የመዝሪያ ቀን ከ25–30 ቀናት ገደማ በኋላ በቆሎውን ከአረም ውድድር፣ ከእድገት ሁኔታና ከሚታዩ የተባይ ወይም የበሽታ ምልክቶች አንጻር ይፈትሹ። ማንኛውንም የቁጥጥር እርምጃ ከአካባቢ የግብርና ምክር ጋር ያስማሙ።",
            ),
        },
        "harvest_preparation": {
            "title": ("Prepare for harvest checks", "ለመከር ምርመራ ይዘጋጁ"),
            "message": (
                "You confirmed a late-season maize stage. Inspect grain maturity and plan harvesting, drying, and clean storage with local extension guidance. This is not a predicted harvest date.",
                "የበቆሎ የመጨረሻ የእድገት ደረጃ መሆኑን አረጋግጠዋል። የእህሉን ብስለት ይፈትሹ፤ መከርን፣ ማድረቅንና ንጹህ ማከማቻን ከአካባቢ የግብርና ምክር ጋር ያቅዱ። ይህ የመከር ቀን ትንበያ አይደለም።",
            ),
        },
    }

    ALERTS = {
        "forecast_heavy_rain": {
            "type": "weather_alert",
            "title": ("Heavy rain in the forecast", "በትንበያው ከባድ ዝናብ አለ"),
            "message": (
                "The seven-day Open-Meteo forecast indicates heavy-rain conditions. Inspect field drainage after rainfall; this forecast does not guarantee local impacts.",
                "የOpen-Meteo የሰባት ቀን ትንበያ ከባድ ዝናብ የሚያመለክቱ ሁኔታዎችን አሳይቷል። ዝናብ ከዘነበ በኋላ የእርሻውን የውሃ ፍሳሽ ይፈትሹ፤ ትንበያው በእርሻዎ ላይ ተጽዕኖ እንደሚኖር አያረጋግጥም።",
            ),
        },
        "dryness_risk": {
            "type": "soil_water_alert",
            "title": ("Modeled dryness risk needs attention", "በሞዴሉ የደረቅነት አደጋ ታይቷል"),
            "message": (
                "The recent weather-based water balance indicates a deficit. This is a model signal, not a sensor measurement. Check field soil moisture and use locally appropriate water-conservation practices.",
                "የቅርብ ጊዜ የአየር ሁኔታ የውሃ ሚዛን እጥረት አመልክቷል። ይህ የሞዴል ምልክት ነው እንጂ የሴንሰር መለኪያ አይደለም። የእርሻውን የአፈር እርጥበት ይመልከቱና ለአካባቢዎ የሚስማሙ ውሃን የመቆጠብ ዘዴዎችን ይጠቀሙ።",
            ),
        },
        "flowering_heat_watch": {
            "type": "agricultural_advisory",
            "title": ("Heat watch during maize flowering", "በበቆሎ አበባ ወቅት የሙቀት ጥንቃቄ"),
            "message": (
                "Current weather and the recorded crop stage meet the advisory's heat-watch conditions. Check the field and seek local extension guidance; this is not a prediction of crop damage.",
                "የአሁኑ የአየር ሁኔታና የተመዘገበው የሰብል ደረጃ የሙቀት ክትትል ሁኔታዎችን አሟልተዋል። እርሻውን ይመልከቱና ከአካባቢ የግብርና ባለሙያ ምክር ይጠይቁ፤ ይህ የሰብል ጉዳት ትንበያ አይደለም።",
            ),
        },
    }
    MISSING_SOIL_INPUTS = (
        "Some information for a reliable root-zone estimate is missing. Save your planting date, farmer-confirmed growth stage, and soil available-water capacity when known. The system will not guess missing values.",
        "ለአስተማማኝ የሥር አካባቢ ውሃ ግምት አንዳንድ መረጃ ጎድሏል። ሲታወቅ የመዝሪያ ቀንዎን፣ በእርስዎ የተረጋገጠ የእድገት ደረጃንና የአፈር የውሃ መያዝ አቅምን ያስቀምጡ። ስርዓቱ የጎደሉ እሴቶችን አይገምትም።",
    )
    SOIL_ESTIMATE_AVAILABLE = (
        "A weather-based root-zone water estimate is now available in your Crop Calendar. It uses modeled weather and saved farm inputs, includes assumptions and uncertainty, and is not a sensor measurement.",
        "በአየር ሁኔታ ላይ የተመሠረተ የሥር አካባቢ የውሃ ግምት አሁን በሰብል ካሌንደርዎ ውስጥ ይገኛል። የሞዴል የአየር መረጃንና ያስቀመጡትን የእርሻ መረጃ ይጠቀማል፤ ግምቶችንና እርግጠኝነት እጥረትን ያካትታል፣ የሴንሰር መለኪያ አይደለም።",
    )

    @classmethod
    def upcoming_activities(cls, profile, *, today: date | None = None) -> list[dict]:
        """Return personalized, dated reminders without inferring a planting date."""
        today = today or cls.local_today(profile)
        planted = getattr(profile, "planting_date", None)
        if not isinstance(planted, date) or planted < today - timedelta(days=365):
            return []
        plans = [
            ("land_preparation", planted - timedelta(days=14), "planting", "land_preparation"),
            ("planting", planted - timedelta(days=1), "planting", "planting"),
            ("weed_inspection", planted + timedelta(days=25), "early_growth", "weed_inspection"),
        ]
        if getattr(profile, "crop_growth_stage", None) == "late_season":
            plans.append(("harvest_preparation", today, "harvest", "harvest_preparation"))
        reminder_days = cls.preferences(profile)["reminder_days_before"]
        earliest_relevant = today - timedelta(days=reminder_days)
        result = []
        for key, scheduled, stage, template_key in plans:
            if earliest_relevant <= scheduled <= today + timedelta(days=60):
                result.append({
                    "activity_key": key,
                    "title": cls.REMINDERS[template_key]["title"][0],
                    "title_am": cls.REMINDERS[template_key]["title"][1],
                    "scheduled_date": scheduled.isoformat(),
                    "reminder_date": (scheduled - timedelta(days=reminder_days)).isoformat(),
                    "stage": stage,
                    "dedupe_key": (
                        f"activity:{getattr(profile, 'user_id', 0)}:{key}:{planted.isoformat()}"
                        if key == "harvest_preparation"
                        else f"activity:{getattr(profile, 'user_id', 0)}:{key}:{scheduled.isoformat()}"
                    ),
                })
        return result

    @classmethod
    def _create_notification(cls, *, user, profile, notification_type, dedupe_key, title, message):
        if FarmerNotification.query.filter_by(user_id=user.id, dedupe_key=dedupe_key).first():
            return None
        item = FarmerNotification(
            user_id=user.id, title_en=title[0], title_am=title[1],
            message_en=message[0], message_am=message[1],
            region=profile.region or "Unknown", notification_type=notification_type,
            dedupe_key=dedupe_key,
        )
        db.session.add(item)
        try:
            db.session.commit()
            return item
        except IntegrityError:
            db.session.rollback()
            return None

    @staticmethod
    def _maybe_send_sms(user, profile, *, message: str, dedupe_key: str) -> None:
        """Send only opt-in urgent alerts, once per exact message; never block in-app."""
        if not profile.sms_opt_in or not user.phone_number:
            return
        # The notification's unique dedupe key is committed before an SMS is
        # attempted; retries therefore never send a second SMS for this event.
        try:
            SMSService.send_sms(
                user.phone_number, message, recipient_type="farmer",
                notification_type="crop_calendar_alert", language=user.preferred_language or "en",
                user_id=user.id, region=profile.region, woreda=profile.woreda, kebele=profile.kebele,
                dedupe_key=dedupe_key,
            )
        except Exception:
            from flask import current_app, has_app_context
            if has_app_context():
                db.session.rollback()
                current_app.logger.exception("Crop-calendar SMS failed (farmer_id=%s, key=%s)", user.id, dedupe_key)
            else:
                import logging
                logging.getLogger(__name__).exception(
                    "Crop-calendar SMS failed (farmer_id=%s, key=%s)", user.id, dedupe_key
                )

    @classmethod
    def _persist_activity(cls, user, profile, plan: dict, *, today: date) -> bool:
        scheduled = date.fromisoformat(plan["scheduled_date"])
        prefs = cls.preferences(profile)
        due = scheduled - timedelta(days=prefs["reminder_days_before"])
        if today < due or today > scheduled or cls.quiet_now(profile):
            return False
        template_key = plan["activity_key"]
        template = cls.REMINDERS[template_key]
        key = plan["dedupe_key"]
        created = cls._create_notification(
            user=user, profile=profile, notification_type="crop_activity",
            dedupe_key=key, title=template["title"], message=template["message"],
        )
        return created is not None

    @classmethod
    def process_farmer(cls, user, profile, *, today: date | None = None, include_weather: bool = True) -> dict:
        """Generate due reminders and provider-backed alerts for one active farmer."""
        today = today or cls.local_today(profile)
        created = {"crop_activity": 0, "weather_alert": 0, "soil_water_alert": 0,
                   "agricultural_advisory": 0, "sms_attempts": 0}
        if not user.is_active or user.role != "farmer" or not profile.region:
            return created

        prefs = cls.preferences(profile)

        if any(getattr(profile, key, None) is None for key in (
            "planting_date", "crop_growth_stage", "available_water_capacity_mm_per_m"
        )):
            key = f"soil_inputs_missing:{today.year}"
            if prefs["categories"]["soil_water_alert"]["in_app"] and cls._create_notification(
                user=user, profile=profile, notification_type="soil_water_alert",
                dedupe_key=key,
                title=("Complete farm inputs for soil-water estimates", "ለአፈር ውሃ ግምት የእርሻ መረጃን ያሟሉ"),
                message=cls.MISSING_SOIL_INPUTS,
            ):
                created["soil_water_alert"] += 1

        for plan in cls.upcoming_activities(profile, today=today):
            scheduled = date.fromisoformat(plan["scheduled_date"])
            due = scheduled - timedelta(days=prefs["reminder_days_before"])
            if due <= today <= scheduled and not cls.quiet_now(profile):
                template = cls.REMINDERS[plan["activity_key"]]
                if prefs["categories"]["crop_activity"]["in_app"] and cls._persist_activity(user, profile, plan, today=today):
                    created["crop_activity"] += 1
                if prefs["categories"]["crop_activity"]["sms"] and profile.sms_opt_in:
                    lang_index = 1 if user.preferred_language == "am" else 0
                    cls._maybe_send_sms(user, profile, message=template["message"][lang_index], dedupe_key=plan["dedupe_key"])

        if not include_weather:
            return created

        latitude, longitude = profile.latitude, profile.longitude
        if latitude is None or longitude is None:
            return created
        lat, lon = float(latitude), float(longitude)
        forecast = historical = current = None
        try:
            forecast = WeatherService.get_forecast_by_coordinates(lat, lon)
        except Exception:
            from flask import current_app
            current_app.logger.exception("Crop reminder forecast unavailable (farmer_id=%s)", user.id)
        end = today - timedelta(days=1)
        start = max(profile.planting_date or (end - timedelta(days=30)), end - timedelta(days=365))
        if start <= end:
            try:
                historical = WeatherService.get_historical_water_weather(lat, lon, start.isoformat(), end.isoformat())
            except Exception:
                from flask import current_app
                current_app.logger.exception("Crop reminder history unavailable (farmer_id=%s)", user.id)
        try:
            current = WeatherService.get_current_weather_by_coordinates(lat, lon)
        except Exception:
            from flask import current_app
            current_app.logger.exception("Crop reminder current weather unavailable (farmer_id=%s)", user.id)

        if current is None and prefs["categories"]["agricultural_advisory"]["in_app"]:
            fallback = cls._create_notification(
                user=user,
                profile=profile,
                notification_type="agricultural_advisory",
                dedupe_key=f"weather_unavailable:{today.isoformat()}",
                title=("Live weather update unavailable", "የቀጥታ የአየር ሁኔታ መረጃ አልተገኘም"),
                message=(
                    "Live weather is temporarily unavailable. Check rainfall and soil moisture in your field before making irrigation or spraying decisions; this notice contains no live measurements.",
                    "የቀጥታ የአየር ሁኔታ መረጃ ለጊዜው አልተገኘም። የመስኖ ወይም የርጭት ውሳኔ ከመወሰንዎ በፊት በእርሻዎ ያለውን ዝናብና የአፈር እርጥበት ይመልከቱ፤ ይህ ማስታወቂያ የቀጥታ መለኪያዎችን አያቀርብም።",
                ),
            )
            created["agricultural_advisory"] += int(fallback is not None)

        try:
            language = user.preferred_language if user.preferred_language in {"en", "am"} else "en"
            calendar = CropCalendarService.get_calendar(
                region=profile.region,
                woreda=profile.woreda,
                kebele=profile.kebele,
                reference_date=today,
                language=language,
            )
            soil = SoilWaterService.calculate(profile, historical, forecast)
            if soil.get("root_zone") is not None and profile.planting_date:
                if prefs["categories"]["soil_water_alert"]["in_app"] and cls._create_notification(
                    user=user, profile=profile, notification_type="soil_water_alert",
                    dedupe_key=f"soil_estimate_available:{profile.planting_date.isoformat()}",
                    title=("Estimated soil-water information is available", "የተገመተ የአፈር ውሃ መረጃ ይገኛል"),
                    message=cls.SOIL_ESTIMATE_AVAILABLE,
                ):
                    created["soil_water_alert"] += 1
            advisories = AgriculturalAdvisoryService.generate(
                profile=profile, calendar=calendar, current_weather=current,
                forecast=forecast, soil_water=soil, historical=historical,
            )
        except Exception:
            from flask import current_app
            current_app.logger.exception("Crop advisory generation failed (farmer_id=%s)", user.id)
            return created

        for advisory in advisories.get("recommendations", []):
            identifier = advisory.get("id")
            template = cls.ALERTS.get(identifier)
            if template is None:
                continue  # Ignore routine stage advice; only action-worthy advisories notify.
            category = template["type"]
            if not prefs["categories"][category]["in_app"]:
                continue
            period = today.isoformat()
            if identifier == "forecast_heavy_rain":
                event_day = next((
                    day.get("date") for day in (forecast or {}).get("days", [])
                    if day.get("weather_code") in (65, 66, 67, 82, 95, 96, 99)
                ), None)
                period = event_day or period
            elif identifier == "dryness_risk":
                period = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
            key = f"{category}:{identifier}:{period}"
            item = cls._create_notification(
                user=user, profile=profile, notification_type=category, dedupe_key=key,
                title=template["title"], message=template["message"],
            )
            if item:
                created[category] += 1
                if advisory.get("priority") == "high":
                    language_index = 1 if user.preferred_language == "am" else 0
                    if prefs["categories"][category]["sms"]:
                        cls._maybe_send_sms(user, profile, message=template["message"][language_index], dedupe_key=key)
                    created["sms_attempts"] += int(bool(profile.sms_opt_in))
        return created

    @classmethod
    def run_daily(cls, *, include_weather: bool = True) -> dict:
        """Process active farmers; failures are isolated per farmer."""
        from flask import current_app
        totals = {"farmers": 0, "failed": 0, "crop_activity": 0, "weather_alert": 0,
                  "soil_water_alert": 0, "agricultural_advisory": 0}
        pairs = (db.session.query(User, FarmerProfile)
                 .join(FarmerProfile, FarmerProfile.user_id == User.id)
                 .filter(User.role == "farmer", User.is_active.is_(True)).all())
        for user, profile in pairs:
            totals["farmers"] += 1
            try:
                counts = cls.process_farmer(user, profile, include_weather=include_weather)
                for key in ("crop_activity", "weather_alert", "soil_water_alert", "agricultural_advisory"):
                    totals[key] += counts[key]
            except Exception:
                db.session.rollback()
                totals["failed"] += 1
                current_app.logger.exception("Scheduled crop notifications failed (farmer_id=%s)", user.id)
        current_app.logger.info("Scheduled crop notifications completed: %s", totals)
        return totals

    @classmethod
    def attach_status(cls, user_id: int, profile) -> list[dict]:
        activities = cls.upcoming_activities(profile)
        if not activities:
            return []
        keys = [item["dedupe_key"] for item in activities]
        rows = FarmerNotification.query.filter(
            FarmerNotification.user_id == user_id,
            FarmerNotification.dedupe_key.in_(keys),
        ).all()
        by_key = {row.dedupe_key: row for row in rows}
        return [{**item,
                 "status": "sent" if item["dedupe_key"] in by_key else "scheduled",
                 "is_read": by_key[item["dedupe_key"]].is_read if item["dedupe_key"] in by_key else None}
                for item in activities]

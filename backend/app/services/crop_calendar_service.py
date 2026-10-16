"""
=========================================================
Crop Calendar Service
=========================================================

Provides Ethiopian maize crop-calendar information.

Supports:
    - English
    - Amharic

The service uses a static agricultural knowledge base
rather than a database table because the core calendar
does not require per-user persistence.

Farmer-specific location information is supplied by the
existing FarmerProfile model in the route layer.

Calendar basis:
    - Land preparation: March - April
    - Planting: April - May
    - Early growth: June
    - Mid-season / crop growth: July - August
    - Harvest: September - December

Actual planting should follow the onset of adequate
rainfall in the farmer's local agro-ecology.

=========================================================
"""

from __future__ import annotations

from datetime import date


class CropCalendarService:
    """
    Service for Ethiopian maize crop-calendar guidance.
    """

    CROP_NAME = "Maize"
    COUNTRY = "Ethiopia"

    SUPPORTED_LANGUAGES = {"en", "am"}

    # =====================================================
    # CALENDAR STAGES
    # =====================================================

    CALENDAR_STAGES = (
        {
            "stage": "land_preparation",
            "label": "Land Preparation",
            "months": [3, 4],
            "month_names": ["March", "April"],
            "activities": [
                "Prepare the farmland before the rainy season.",
                "Clear weeds and prepare the seedbed.",
                "Use crop residues or other soil-cover practices "
                "to reduce erosion and conserve moisture.",
            ],
        },
        {
            "stage": "planting",
            "label": "Planting",
            "months": [4, 5],
            "month_names": ["April", "May"],
            "activities": [
                "Plant maize when sufficient soil moisture is "
                "available at the onset of the rainy season.",
                "Use row planting where possible.",
                "Use locally recommended maize varieties "
                "appropriate for the agro-ecology.",
            ],
        },
        {
            "stage": "early_growth",
            "label": "Early Growth",
            "months": [6],
            "month_names": ["June"],
            "activities": [
                "Check germination and plant establishment.",
                "Control weeds early.",
                "Monitor the field for disease and pest symptoms.",
            ],
        },
        {
            "stage": "mid_season",
            "label": "Mid-Season / Crop Growth",
            "months": [7, 8],
            "month_names": ["July", "August"],
            "activities": [
                "Keep the field free from serious weed competition.",
                "Monitor maize leaves regularly for disease symptoms.",
                "Maintain adequate soil moisture where possible.",
                "Inspect the crop during flowering and grain formation.",
            ],
        },
        {
            "stage": "harvest",
            "label": "Harvest",
            "months": [9, 10, 11, 12],
            "month_names": [
                "September",
                "October",
                "November",
                "December",
            ],
            "activities": [
                "Monitor grain maturity before harvesting.",
                "Harvest at the appropriate maturity stage.",
                "Dry harvested maize properly to reduce storage problems.",
                "Store grain in a clean and dry location.",
            ],
        },
    )

    # =====================================================
    # AMHARIC TRANSLATIONS
    # =====================================================

    AMHARIC_STAGES = {
        "land_preparation": {
            "label": "የመሬት ዝግጅት",
            "activities": [
                "ከዝናብ ወቅት በፊት የእርሻ መሬቱን ያዘጋጁ።",
                "አረምን ያስወግዱ እና የዘር መደቡን ያዘጋጁ።",
                "የአፈር መሸርሸርን ለመቀነስና እርጥበትን "
                "ለመጠበቅ የሰብል ተረፈ ምርት ወይም ሌሎች "
                "የአፈር መሸፈኛ ዘዴዎችን ይጠቀሙ።",
            ],
        },
        "planting": {
            "label": "የመዝራት ወቅት",
            "activities": [
                "በዝናብ ወቅት መጀመሪያ ላይ በቂ የአፈር እርጥበት "
                "ሲኖር በቆሎን ይዝሩ።",
                "ከተቻለ በረድፍ የመዝራት ዘዴን ይጠቀሙ።",
                "ለአካባቢው የአየር ንብረትና የእርሻ ሁኔታ "
                "የሚመከሩ የበቆሎ ዝርያዎችን ይጠቀሙ።",
            ],
        },
        "early_growth": {
            "label": "የቅድመ እድገት ወቅት",
            "activities": [
                "የዘሩ መብቀልና የተክሉን መመስረት ይከታተሉ።",
                "አረምን በቶሎ ይቆጣጠሩ።",
                "የበሽታና የተባይ ምልክቶችን በመስኩ ላይ ይከታተሉ።",
            ],
        },
        "mid_season": {
            "label": "የመካከለኛ እድገት ወቅት",
            "activities": [
                "መስኩን ከከባድ የአረም ውድድር ነፃ ያድርጉ።",
                "የበቆሎ ቅጠሎችን በየጊዜው በመመልከት "
                "የበሽታ ምልክቶችን ይከታተሉ።",
                "ከተቻለ በቂ የአፈር እርጥበት ያስጠብቁ።",
                "በአበባ እና በእህል አፈጣጠር ወቅት ሰብሉን በጥንቃቄ "
                "ይመልከቱ።",
            ],
        },
        "harvest": {
            "label": "የመከር ወቅት",
            "activities": [
                "ከመከር በፊት የእህሉን የብስለት ሁኔታ ይከታተሉ።",
                "በተገቢው የብስለት ደረጃ ላይ መከር ያድርጉ።",
                "ከተሰበሰበ በኋላ የማከማቻ ችግሮችን ለመቀነስ "
                "በቂ ማድረቅ ያድርጉ።",
                "የተሰበሰበውን እህል በንፁህና ደረቅ ቦታ ያከማቹ።",
            ],
        },
        "off_season": {
            "label": "የወቅቱ ውጭ",
            "activities": [
                "ለሚቀጥለው የበቆሎ ምርት ወቅት ይዘጋጁ።",
                "የቀድሞውን የሰብል አፈፃፀም ይገምግሙ።",
                "ዘርና የእርሻ ግብዓቶችን ያዘጋጁ።",
                "የአካባቢውን ዝናብና የግብርና ምክር ይከታተሉ።",
            ],
        },
    }

    AMHARIC_MONTHS = {
        1: "ጃንዩወሪ",
        2: "ፌብሩወሪ",
        3: "ማርች",
        4: "ኤፕሪል",
        5: "ሜይ",
        6: "ጁን",
        7: "ጁላይ",
        8: "ኦገስት",
        9: "ሴፕቴምበር",
        10: "ኦክቶበር",
        11: "ኖቬምበር",
        12: "ዲሴምበር",
    }

    AMHARIC_REGIONAL_GUIDANCE = {
        "amhara": (
            "የበቆሎ ምርት በአጠቃላይ ከዋናው የዝናብ ወቅት "
            "ጋር ተያይዞ መካሄድ አለበት። የመዝራት ጊዜ "
            "በአካባቢው በቂ ዝናብ በሚጀምርበት ጊዜ መሠረት "
            "መስተካከል አለበት።"
        ),
        "oromia": (
            "የበቆሎ መዝራት በአካባቢው በቂ ዝናብ መጀመሩን "
            "ተከትሎ መካሄድ አለበት።"
        ),
        "benishangul gumuz": (
            "የመዝራት ጊዜ ከበቂ የአፈር እርጥበትና "
            "ከአካባቢው የዝናብ ወቅት ጋር መጣጣም አለበት።"
        ),
        "snnpr": (
            "የካሌንደሩ ጊዜ ከአካባቢው የዝናብና "
            "የአየር ንብረት ሁኔታ ጋር መስማማት አለበት።"
        ),
        "sidama": (
            "የመዝራት ጊዜ በቂ ዝናብና በአካባቢው "
            "የሚሰጡ የግብርና ምክሮችን ተከትሎ መሆን አለበት።"
        ),
    }

    AMHARIC_SEASONS = {
        "main_meher": "ዋናው የመስከረም ዝናብ ወቅት",
        "main_rainy": "ዋናው የዝናብ ወቅት",
    }

    # =====================================================
    # REGIONAL GUIDANCE
    # =====================================================

    REGIONAL_GUIDANCE = {
        "amhara": {
            "region": "Amhara",
            "season": "Main Meher season",
            "guidance": (
                "Maize production should generally follow the "
                "main rainy season. Planting should be adjusted "
                "to the local onset of adequate rainfall."
            ),
        },
        "oromia": {
            "region": "Oromia",
            "season": "Main Meher season",
            "guidance": (
                "Maize planting should follow the onset of "
                "adequate rainfall in the local production area."
            ),
        },
        "benishangul gumuz": {
            "region": "Benishangul-Gumuz",
            "season": "Main rainy season",
            "guidance": (
                "Planting should be synchronized with adequate "
                "soil moisture and the local rainy season."
            ),
        },
        "snnpr": {
            "region": "SNNPR",
            "season": "Main rainy season",
            "guidance": (
                "Calendar timing should follow local rainfall "
                "and agro-ecological conditions."
            ),
        },
        "sidama": {
            "region": "Sidama",
            "season": "Main rainy season",
            "guidance": (
                "Planting should follow sufficient rainfall and "
                "local agricultural recommendations."
            ),
        },
    }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    @staticmethod
    def _normalize_region(region: str | None) -> str:
        """
        Normalize a region name for lookup.
        """

        if region is None:
            return ""

        return " ".join(
            str(region).strip().lower().split()
        )

    @classmethod
    def _normalize_language(cls, language: str | None) -> str:
        """
        Normalize and validate the requested language.
        """

        language = str(language or "en").strip().lower()

        if language not in cls.SUPPORTED_LANGUAGES:
            return "en"

        return language

    # =====================================================
    # CURRENT STAGE
    # =====================================================

    @classmethod
    def _get_current_stage(
        cls,
        month: int,
        language: str = "en",
    ) -> dict:
        """
        Determine the current crop-calendar stage.
        """

        language = cls._normalize_language(language)

        for stage in cls.CALENDAR_STAGES:

            if month in stage["months"]:

                if language == "am":
                    translation = cls.AMHARIC_STAGES[
                        stage["stage"]
                    ]

                    return {
                        "stage": stage["stage"],
                        "label": translation["label"],
                        "month": month,
                        "month_name": cls.AMHARIC_MONTHS[month],
                        "activities": list(
                            translation["activities"]
                        ),
                    }

                return {
                    "stage": stage["stage"],
                    "label": stage["label"],
                    "month": month,
                    "month_name": date(
                        2000,
                        month,
                        1,
                    ).strftime("%B"),
                    "activities": list(
                        stage["activities"]
                    ),
                }

        if language == "am":
            translation = cls.AMHARIC_STAGES["off_season"]

            return {
                "stage": "off_season",
                "label": translation["label"],
                "month": month,
                "month_name": cls.AMHARIC_MONTHS[month],
                "activities": list(
                    translation["activities"]
                ),
            }

        return {
            "stage": "off_season",
            "label": "Off Season",
            "month": month,
            "month_name": date(
                2000,
                month,
                1,
            ).strftime("%B"),
            "activities": [
                "Prepare for the next maize production season.",
                "Review previous crop performance.",
                "Prepare seed and farm inputs.",
                "Monitor local rainfall and agricultural advice.",
            ],
        }

    # =====================================================
    # CALENDAR
    # =====================================================

    @classmethod
    def get_calendar(
        cls,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        reference_date: date | None = None,
        language: str = "en",
    ) -> dict:
        """
        Return the maize crop calendar for a farmer's
        existing agricultural location.

        Supported languages:
            - en
            - am
        """

        if not isinstance(region, str) or not region.strip():
            raise ValueError(
                "Farmer region is required."
            )

        if reference_date is None:
            reference_date = date.today()

        language = cls._normalize_language(language)

        normalized_region = cls._normalize_region(
            region
        )

        regional_info = cls.REGIONAL_GUIDANCE.get(
            normalized_region
        )

        if regional_info is None:
            regional_info = {
                "region": region.strip(),
                "season": "Main rainy season",
                "guidance": (
                    "Adjust planting according to the onset "
                    "of adequate local rainfall and advice "
                    "from agricultural extension services."
                ),
            }

        current_stage = cls._get_current_stage(
            reference_date.month,
            language=language,
        )

        stages = []

        for stage in cls.CALENDAR_STAGES:

            if language == "am":
                translation = cls.AMHARIC_STAGES[
                    stage["stage"]
                ]

                stages.append(
                    {
                        "stage": stage["stage"],
                        "label": translation["label"],
                        "months": [
                            cls.AMHARIC_MONTHS[month]
                            for month in stage["months"]
                        ],
                        "activities": list(
                            translation["activities"]
                        ),
                    }
                )

            else:
                stages.append(
                    {
                        "stage": stage["stage"],
                        "label": stage["label"],
                        "months": list(
                            stage["month_names"]
                        ),
                        "activities": list(
                            stage["activities"]
                        ),
                    }
                )

        if language == "am":
            season = (
                cls.AMHARIC_SEASONS["main_meher"]
                if regional_info["season"]
                == "Main Meher season"
                else cls.AMHARIC_SEASONS["main_rainy"]
            )

            guidance = cls.AMHARIC_REGIONAL_GUIDANCE.get(
                normalized_region,
                "የመዝራት ጊዜ በአካባቢው በቂ ዝናብና "
                "በግብርና ባለሙያዎች ምክር መሠረት "
                "መስተካከል አለበት።",
            )

            crop_name = "በቆሎ"
            country = "ኢትዮጵያ"

        else:
            season = regional_info["season"]
            guidance = regional_info["guidance"]
            crop_name = cls.CROP_NAME
            country = cls.COUNTRY

        return {
            "crop": crop_name,
            "country": country,
            "language": language,
            "location": {
                "region": region.strip(),
                "woreda": (
                    woreda.strip()
                    if isinstance(woreda, str)
                    and woreda.strip()
                    else None
                ),
                "kebele": (
                    kebele.strip()
                    if isinstance(kebele, str)
                    and kebele.strip()
                    else None
                ),
            },
            "season": season,
            "regional_guidance": guidance,
            "reference_date": reference_date.isoformat(),
            "current_stage": current_stage,
            "calendar": stages,
        }
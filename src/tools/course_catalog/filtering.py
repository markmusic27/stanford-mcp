from typing import Any, Dict, Iterable, List, Optional
import explorecourses.filters as filters


# Mappings for converting user-provided strings to ExploreCourses filters
TERM_MAP = {
    "autumn": filters.AUTUMN,
    "winter": filters.WINTER,
    "spring": filters.SPRING,
    "summer": filters.SUMMER,
}

UG_MAP = {
    "language": filters.LANGUAGE,
    "writing1": filters.WRITING1,
    "writing2": filters.WRITING2,
    "writingsle": filters.WRITINGSLE,
    "way_aii": filters.WAY_AII,
    "way_aqr": filters.WAY_AQR,
    "way_ce": filters.WAY_CE,
    "way_ed": filters.WAY_ED,
    "way_er": filters.WAY_ER,
    "way_fr": filters.WAY_FR,
    "way_si": filters.WAY_SI,
    "way_sma": filters.WAY_SMA,
}

UNITS_MAP = {
    "1": filters.UNITS_1,
    "2": filters.UNITS_2,
    "3": filters.UNITS_3,
    "4": filters.UNITS_4,
    "5": filters.UNITS_5,
    "gt5": filters.UNITS_GT5,
    "units_1": filters.UNITS_1,
    "units_2": filters.UNITS_2,
    "units_3": filters.UNITS_3,
    "units_4": filters.UNITS_4,
    "units_5": filters.UNITS_5,
    "units_gt5": filters.UNITS_GT5,
}

TIME_MAP = {
    "early_morning": filters.TIME_EARLY_MORNING,
    "morning": filters.TIME_MORNING,
    "lunchtime": filters.TIME_LUNCHTIME,
    "afternoon": filters.TIME_AFTERNOON,
    "evening": filters.TIME_EVENING,
    "time_early_morning": filters.TIME_EARLY_MORNING,
    "time_morning": filters.TIME_MORNING,
    "time_lunchtime": filters.TIME_LUNCHTIME,
    "time_afternoon": filters.TIME_AFTERNOON,
    "time_evening": filters.TIME_EVENING,
}

DAY_MAP = {
    "sunday": filters.DAY_SUNDAY,
    "monday": filters.DAY_MONDAY,
    "tuesday": filters.DAY_TUESDAY,
    "wednesday": filters.DAY_WEDNESDAY,
    "thursday": filters.DAY_THURSDAY,
    "friday": filters.DAY_FRIDAY,
    "saturday": filters.DAY_SATURDAY,
    "day_sunday": filters.DAY_SUNDAY,
    "day_monday": filters.DAY_MONDAY,
    "day_tuesday": filters.DAY_TUESDAY,
    "day_wednesday": filters.DAY_WEDNESDAY,
    "day_thursday": filters.DAY_THURSDAY,
    "day_friday": filters.DAY_FRIDAY,
    "day_saturday": filters.DAY_SATURDAY,
}

CAREER_MAP = {
    "ug": filters.CAREER_UG,
    "gr": filters.CAREER_GR,
    "gsb": filters.CAREER_GSB,
    "law": filters.CAREER_LAW,
    "med": filters.CAREER_MED,
    "career_ug": filters.CAREER_UG,
    "career_gr": filters.CAREER_GR,
    "career_gsb": filters.CAREER_GSB,
    "career_law": filters.CAREER_LAW,
    "career_med": filters.CAREER_MED,
}


def _extend_filters_from_list(values: Optional[Iterable[str]], mapping: Dict[str, str], fs: List[str], seen: set, label: str) -> None:
    if not values:
        return
    if not isinstance(values, list):
        raise TypeError(f"'{label}' must be an array of strings if provided.")
    for v in values:
        if not isinstance(v, str):
            raise TypeError(f"Each value in '{label}' must be a string.")
        key = v.strip().lower()
        if not key:
            continue
        if key not in mapping:
            raise ValueError(f"Invalid value '{v}' for {label}.")
        fval = mapping[key]
        if fval not in seen:
            fs.append(fval)
            seen.add(fval)


def build_filters_from_arguments(arguments: Dict[str, Any], *, term_field: str = "terms", require_terms: bool = True, default_terms: Optional[Iterable[str]] = None) -> List[str]:
    """
    Build ExploreCourses filter tokens from incoming handler arguments.

    - If require_terms is True, the input must include a non-empty list under term_field.
    - If require_terms is False and no terms provided, default_terms (if given) will be used.
    - Optional filters (ug_reqs, units, times, days, careers) are included when present.
    """

    fs: List[str] = []
    seen: set = set()

    # Terms
    terms = arguments.get(term_field)
    if require_terms:
        if not isinstance(terms, list) or len(terms) == 0:
            raise ValueError(f"'{term_field}' must be a non-empty array of term names.")
    else:
        if not terms and default_terms:
            terms = list(default_terms)

    if terms:
        for t in terms:
            if not isinstance(t, str):
                raise TypeError("Each term must be a string.")
            key = t.strip().lower()
            if key not in TERM_MAP:
                valid = ", ".join(["Autumn", "Winter", "Spring", "Summer"])
                raise ValueError(f"Invalid term '{t}'. Valid options: {valid}")
            tok = TERM_MAP[key]
            if tok not in seen:
                fs.append(tok)
                seen.add(tok)

    # Optional filters
    _extend_filters_from_list(arguments.get("ug_reqs"), UG_MAP, fs, seen, "ug_reqs")
    _extend_filters_from_list(arguments.get("units"), UNITS_MAP, fs, seen, "units")
    _extend_filters_from_list(arguments.get("times"), TIME_MAP, fs, seen, "times")
    _extend_filters_from_list(arguments.get("days"), DAY_MAP, fs, seen, "days")
    _extend_filters_from_list(arguments.get("careers"), CAREER_MAP, fs, seen, "careers")

    return fs



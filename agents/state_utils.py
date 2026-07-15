"""US state helpers for multi-state pipeline filtering."""

from __future__ import annotations

# State FIPS prefix (2-digit) → abbreviation
FIPS_TO_STATE: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY",
}

STATE_TO_FIPS: dict[str, str] = {v: k for k, v in FIPS_TO_STATE.items()}

STATE_TO_NAME: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def parse_state_filter(state_filter: str | list[str] | None) -> list[str] | None:
    """
    Parse state filter into list of abbreviations, or None for ALL states.

    Examples: 'GA' → ['GA'], 'GA,FL' → ['GA','FL'], 'ALL' → None
    """
    if state_filter is None:
        return ["GA"]
    if isinstance(state_filter, list):
        tokens = state_filter
    else:
        tokens = [s.strip().upper() for s in str(state_filter).split(",") if s.strip()]

    if not tokens or tokens == ["ALL"]:
        return None

    for t in tokens:
        if t not in STATE_TO_FIPS:
            raise ValueError(f"Unknown state abbreviation: {t}")
    return tokens


def state_fips_prefix(state_abbr: str) -> str:
    return STATE_TO_FIPS[state_abbr]


def county_fips_to_state(county_fips: str) -> str:
    return FIPS_TO_STATE.get(str(county_fips)[:2].zfill(2), "")


def state_label(states: list[str] | None) -> str:
    if states is None:
        return "ALL"
    return ",".join(states)

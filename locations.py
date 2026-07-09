"""
Location reference data for the dependent Country → Region → Municipality
selectors (spec §6).

Design honesty (spec §6): we only claim the administrative detail we actually
hold. South Africa — the app's primary market — is populated to municipality
level. Other countries carry a validated country name plus level-1 regions
where those are well-known and stable (states / provinces / nations); below
that we say so plainly rather than pretending to have every local authority.
Every level uses a fixed, searchable option list, so arbitrary free text can
never be submitted for a country or a known region.

The public helpers are the only API the UI and validation should use:
  country_options(), is_country(), region_term(), region_options(),
  municipality_term(), municipality_options(), NOT_LISTED.

Canonical validation helpers (shared by BOTH the manual picker and the AI/chat
path via schema.merge_updates, so no flow can store an unrecognised location):
  canonical_country(), canonical_region(), canonical_municipality(),
  resolve_location().
"""

import re

# Sentinel option offered at the end of every known region/municipality list so
# people in areas we don't itemise can still proceed (stored as "" upstream).
NOT_LISTED = "Other / not listed"

# Comprehensive, stable list of sovereign countries (UN members + a few widely
# used territories). Alphabetical; used verbatim as the validated option set.
COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola",
    "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria",
    "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus",
    "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
    "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde",
    "Central African Republic", "Chad", "Chile", "China", "Colombia",
    "Comoros", "Congo (Brazzaville)", "Congo (Kinshasa)", "Costa Rica",
    "Côte d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czechia", "Denmark",
    "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini",
    "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia",
    "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea",
    "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hong Kong", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel",
    "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
    "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar",
    "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands",
    "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco",
    "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia",
    "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger",
    "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan",
    "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines",
    "Samoa", "San Marino", "São Tomé and Príncipe", "Saudi Arabia", "Senegal",
    "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia",
    "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan",
    "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
    "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo",
    "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
    "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City",
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
]

# South Africa to municipality level: the 8 metropolitan municipalities plus
# the district municipalities of each province (stable, official). Names are
# chosen to fuzzy-match the tariff table keys in tariffs.py where relevant.
_ZA = {
    "term": "Province",
    "sub_term": "Municipality / metro",
    "regions": {
        "Eastern Cape": [
            "Buffalo City (metro)", "Nelson Mandela Bay (metro)",
            "Alfred Nzo District", "Amathole District", "Chris Hani District",
            "Joe Gqabi District", "OR Tambo District", "Sarah Baartman District",
        ],
        "Free State": [
            "Mangaung (metro)", "Fezile Dabi District", "Lejweleputswa District",
            "Thabo Mofutsanyana District", "Xhariep District",
        ],
        "Gauteng": [
            "City of Johannesburg (metro)", "City of Tshwane (metro)",
            "City of Ekurhuleni (metro)", "Sedibeng District",
            "West Rand District",
        ],
        "KwaZulu-Natal": [
            "eThekwini (metro)", "Amajuba District", "Harry Gwala District",
            "iLembe District", "King Cetshwayo District", "Ugu District",
            "uMgungundlovu District", "uMkhanyakude District",
            "uMzinyathi District", "uThukela District", "Zululand District",
        ],
        "Limpopo": [
            "Capricorn District", "Mopani District", "Sekhukhune District",
            "Vhembe District", "Waterberg District",
        ],
        "Mpumalanga": [
            "Ehlanzeni District", "Gert Sibande District",
            "Nkangala District",
        ],
        "North West": [
            "Bojanala Platinum District", "Dr Kenneth Kaunda District",
            "Dr Ruth Segomotsi Mompati District", "Ngaka Modiri Molema District",
        ],
        "Northern Cape": [
            "Frances Baard District", "John Taolo Gaetsewe District",
            "Namakwa District", "Pixley ka Seme District", "ZF Mgcawu District",
        ],
        "Western Cape": [
            "City of Cape Town (metro)", "Cape Winelands District",
            "Central Karoo District", "Garden Route District",
            "Overberg District", "West Coast District",
        ],
    },
}

# Level-1 regions for other countries where the list is well-known and stable.
# No municipality level is claimed for these (sub_term omitted).
_US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

SUBDIVISIONS = {
    "South Africa": _ZA,
    "United States": {"term": "State", "regions": {s: [] for s in _US_STATES}},
    "United Kingdom": {"term": "Nation", "regions": {
        "England": [], "Scotland": [], "Wales": [], "Northern Ireland": []}},
    "Canada": {"term": "Province / Territory", "regions": {r: [] for r in [
        "Alberta", "British Columbia", "Manitoba", "New Brunswick",
        "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
        "Nunavut", "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan",
        "Yukon"]}},
    "Australia": {"term": "State / Territory", "regions": {r: [] for r in [
        "Australian Capital Territory", "New South Wales", "Northern Territory",
        "Queensland", "South Australia", "Tasmania", "Victoria",
        "Western Australia"]}},
    "Namibia": {"term": "Region", "regions": {r: [] for r in [
        "Erongo", "Hardap", "ǁKaras", "Kavango East", "Kavango West", "Khomas",
        "Kunene", "Ohangwena", "Omaheke", "Omusati", "Oshana", "Oshikoto",
        "Otjozondjupa", "Zambezi"]}},
    "Botswana": {"term": "District", "regions": {r: [] for r in [
        "Central", "Chobe", "Ghanzi", "Kgalagadi", "Kgatleng", "Kweneng",
        "North East", "North West", "South East", "Southern"]}},
    "Zimbabwe": {"term": "Province", "regions": {r: [] for r in [
        "Bulawayo", "Harare", "Manicaland", "Mashonaland Central",
        "Mashonaland East", "Mashonaland West", "Masvingo", "Matabeleland North",
        "Matabeleland South", "Midlands"]}},
    # Kenya's 47 constitutional counties (2010) — official, stable level-1 list.
    "Kenya": {"term": "County", "regions": {r: [] for r in [
        "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu",
        "Garissa", "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho",
        "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale",
        "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit",
        "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi",
        "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya",
        "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia",
        "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"]}},
    # Nigeria's 36 states plus the Federal Capital Territory — official list.
    "Nigeria": {"term": "State", "regions": {r: [] for r in [
        "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
        "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti",
        "Enugu", "Federal Capital Territory", "Gombe", "Imo", "Jigawa",
        "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos",
        "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau",
        "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara"]}},
}


def country_options():
    return list(COUNTRIES)


def is_country(name):
    return name in COUNTRIES


def _entry(country):
    return SUBDIVISIONS.get(country)


def has_regions(country):
    e = _entry(country)
    return bool(e and e.get("regions"))


def region_term(country):
    e = _entry(country)
    return (e or {}).get("term", "Region / Province")


def region_options(country):
    """Validated level-1 options for a country, or [] when we don't hold them.
    A NOT_LISTED escape is appended so users are never blocked."""
    e = _entry(country)
    if not e or not e.get("regions"):
        return []
    return sorted(e["regions"].keys()) + [NOT_LISTED]


def municipality_term(country):
    e = _entry(country)
    return (e or {}).get("sub_term", "Municipality / local authority")


def has_municipalities(country, region):
    e = _entry(country)
    return bool(e and region and e.get("regions", {}).get(region))


def municipality_options(country, region):
    """Validated municipality options for a (country, region), or [] when we
    don't itemise them. NOT_LISTED escape appended when we do."""
    e = _entry(country)
    if not e or not region:
        return []
    munis = e.get("regions", {}).get(region)
    if not munis:
        return []
    return list(munis) + [NOT_LISTED]


# ---------------------------------------------------------------------------
# Canonical validation — the single rule both the manual picker AND the AI/chat
# merge run through, so an arbitrary string can never be stored as a structured
# location value (spec §6). Matching is tolerant of case/punctuation; genuinely
# ambiguous input returns None so the caller can ask the user to clarify.
# ---------------------------------------------------------------------------

_COUNTRY_BY_LOWER = {c.lower(): c for c in COUNTRIES}

# Small, deliberately unambiguous set of informal names / abbreviations. Only
# clearly-one-country entries belong here; anything ambiguous is left out so it
# resolves to None and the assistant asks rather than guessing.
_COUNTRY_ALIASES = {
    "usa": "United States", "u.s.a.": "United States", "u.s.": "United States",
    "us": "United States", "united states of america": "United States",
    "america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "great britain": "United Kingdom",
    "rsa": "South Africa",
    "uae": "United Arab Emirates",
    "drc": "Congo (Kinshasa)", "dr congo": "Congo (Kinshasa)",
    "ivory coast": "Côte d'Ivoire",
    "swaziland": "Eswatini",
    "czech republic": "Czechia",
    "burma": "Myanmar",
    "cabo verde": "Cape Verde",
}


def _simplify(s):
    """Lowercase, keep only letters/digits — for tolerant name comparison."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _muni_core(s):
    """A municipality name reduced to its distinctive core: strip the
    '(metro)' / 'district' / 'municipality' / 'city of' scaffolding so a user
    saying 'Cape Town' can match 'City of Cape Town (metro)'."""
    s = (s or "").lower().replace("(metro)", " ")
    s = re.sub(r"\b(metro|metropolitan|district|municipality|local|city of)\b",
               " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def canonical_country(value):
    """Canonical country name for a user/AI string, or None if not clearly a
    recognised country. Case-insensitive; accepts a few common aliases."""
    if not isinstance(value, str):
        return None
    key = value.strip().lower()
    if not key:
        return None
    return _COUNTRY_BY_LOWER.get(key) or _COUNTRY_ALIASES.get(key)


def canonical_region(country, value):
    """Canonical level-1 region for a country, or None when the country has no
    region data or the value doesn't unambiguously match one."""
    if not isinstance(value, str) or not value.strip():
        return None
    e = _entry(canonical_country(country) or country)
    if not e or not e.get("regions"):
        return None
    regions = list(e["regions"].keys())
    key = value.strip().lower()
    for name in regions:
        if name.lower() == key:
            return name
    vsimp = _simplify(value)
    if not vsimp:
        return None
    exact = [n for n in regions if _simplify(n) == vsimp]
    if len(exact) == 1:
        return exact[0]
    subs = [n for n in regions
            if vsimp in _simplify(n) or _simplify(n) in vsimp]
    return subs[0] if len(subs) == 1 else None


def canonical_municipality(country, region, value):
    """Canonical municipality/local authority for a (country, region), or None
    when we hold no municipality data for that region or the value doesn't
    unambiguously match one. Never invents a municipality."""
    if not isinstance(value, str) or not value.strip():
        return None
    c = canonical_country(country) or country
    r = canonical_region(c, region) or region
    munis = (_entry(c) or {}).get("regions", {}).get(r) or []
    if not munis:
        return None
    key = value.strip().lower()
    for name in munis:
        if name.lower() == key:
            return name
    vcore = _muni_core(value)
    if not vcore:
        return None
    exact = [n for n in munis if _muni_core(n) == vcore]
    if len(exact) == 1:
        return exact[0]
    subs = [n for n in munis
            if vcore in _muni_core(n) or _muni_core(n) in vcore]
    return subs[0] if len(subs) == 1 else None


def resolve_location(country=None, region=None, municipality=None):
    """Cross-consistent canonical (country, region, municipality) triple.

    Enforced top-down, so a downstream field is cleared whenever an upstream
    field changes or fails to validate (spec §6):
      * an unrecognised country empties all three;
      * a region invalid for / absent from the country empties region AND
        municipality;
      * a municipality invalid for / unavailable in the region empties
        municipality.
    Empty string means "not set — use the broader fallback"; nothing is ever
    invented. This is the ONE rule the manual picker and the AI/chat merge share.
    """
    c = canonical_country(country) or ""
    if not c:
        return "", "", ""
    r = ""
    if region:
        r = canonical_region(c, region) or ""
    m = ""
    if r and municipality:
        m = canonical_municipality(c, r, municipality) or ""
    return c, r, m

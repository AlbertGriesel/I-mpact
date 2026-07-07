"""
Airport database and great-circle distance calculation.

Flight distance is calculated automatically from airport coordinates with the
Haversine formula (spec §10.1, calc doc §8) instead of asking users to
estimate distances. Coordinates are approximate (±0.1° is irrelevant at
flight scale). The set focuses on South African and African airports plus the
major international hubs South Africans actually fly to.
"""

import math

# IATA code: (airport name, city, country, latitude, longitude)
AIRPORTS = {
    # --- South Africa
    "JNB": ("O.R. Tambo International", "Johannesburg", "South Africa", -26.14, 28.24),
    "HLA": ("Lanseria International", "Johannesburg", "South Africa", -25.94, 27.93),
    "CPT": ("Cape Town International", "Cape Town", "South Africa", -33.97, 18.60),
    "DUR": ("King Shaka International", "Durban", "South Africa", -29.61, 31.12),
    "PLZ": ("Chief Dawid Stuurman International", "Gqeberha (Port Elizabeth)", "South Africa", -33.98, 25.62),
    "ELS": ("King Phalo", "East London", "South Africa", -33.04, 27.83),
    "GRJ": ("George", "George", "South Africa", -34.01, 22.38),
    "BFN": ("Bram Fischer International", "Bloemfontein", "South Africa", -29.09, 26.30),
    "KIM": ("Kimberley", "Kimberley", "South Africa", -28.80, 24.77),
    "MQP": ("Kruger Mpumalanga International", "Mbombela (Nelspruit)", "South Africa", -25.38, 31.10),
    "PTG": ("Polokwane International", "Polokwane", "South Africa", -23.85, 29.46),
    "UTN": ("Upington", "Upington", "South Africa", -28.40, 21.26),
    "RCB": ("Richards Bay", "Richards Bay", "South Africa", -28.74, 32.09),
    "UTT": ("Mthatha", "Mthatha", "South Africa", -31.55, 28.67),
    "MGH": ("Margate", "Margate", "South Africa", -30.86, 30.34),
    "PHW": ("Hoedspruit Eastgate", "Phalaborwa/Hoedspruit", "South Africa", -24.35, 31.05),
    # --- Southern Africa
    "WDH": ("Hosea Kutako International", "Windhoek", "Namibia", -22.48, 17.47),
    "GBE": ("Sir Seretse Khama International", "Gaborone", "Botswana", -24.56, 25.92),
    "MUB": ("Maun", "Maun", "Botswana", -19.97, 23.43),
    "MPM": ("Maputo International", "Maputo", "Mozambique", -25.92, 32.57),
    "VFA": ("Victoria Falls", "Victoria Falls", "Zimbabwe", -18.10, 25.84),
    "HRE": ("Robert Gabriel Mugabe International", "Harare", "Zimbabwe", -17.93, 31.09),
    "LUN": ("Kenneth Kaunda International", "Lusaka", "Zambia", -15.33, 28.45),
    "LLW": ("Kamuzu International", "Lilongwe", "Malawi", -13.79, 33.78),
    "MSU": ("Moshoeshoe I International", "Maseru", "Lesotho", -29.46, 27.55),
    "SHO": ("King Mswati III International", "Manzini", "Eswatini", -26.36, 31.72),
    "TNR": ("Ivato International", "Antananarivo", "Madagascar", -18.80, 47.48),
    "MRU": ("Sir Seewoosagur Ramgoolam International", "Mauritius", "Mauritius", -20.43, 57.68),
    "SEZ": ("Seychelles International", "Mahé", "Seychelles", -4.67, 55.52),
    "LAD": ("Quatro de Fevereiro", "Luanda", "Angola", -8.86, 13.23),
    # --- East Africa
    "NBO": ("Jomo Kenyatta International", "Nairobi", "Kenya", -1.32, 36.93),
    "MBA": ("Moi International", "Mombasa", "Kenya", -4.03, 39.59),
    "DAR": ("Julius Nyerere International", "Dar es Salaam", "Tanzania", -6.88, 39.20),
    "JRO": ("Kilimanjaro International", "Kilimanjaro", "Tanzania", -3.43, 37.07),
    "ZNZ": ("Abeid Amani Karume International", "Zanzibar", "Tanzania", -6.22, 39.22),
    "EBB": ("Entebbe International", "Entebbe/Kampala", "Uganda", 0.04, 32.44),
    "KGL": ("Kigali International", "Kigali", "Rwanda", -1.97, 30.14),
    "ADD": ("Addis Ababa Bole International", "Addis Ababa", "Ethiopia", 8.98, 38.80),
    "JUB": ("Juba International", "Juba", "South Sudan", 4.87, 31.60),
    "KRT": ("Khartoum International", "Khartoum", "Sudan", 15.59, 32.55),
    # --- Central / West Africa
    "FIH": ("N'djili International", "Kinshasa", "DR Congo", -4.39, 15.44),
    "DLA": ("Douala International", "Douala", "Cameroon", 4.01, 9.72),
    "NSI": ("Yaoundé Nsimalen International", "Yaoundé", "Cameroon", 3.72, 11.55),
    "LOS": ("Murtala Muhammed International", "Lagos", "Nigeria", 6.58, 3.32),
    "ABV": ("Nnamdi Azikiwe International", "Abuja", "Nigeria", 9.01, 7.26),
    "ACC": ("Kotoka International", "Accra", "Ghana", 5.61, -0.17),
    "ABJ": ("Félix-Houphouët-Boigny International", "Abidjan", "Côte d'Ivoire", 5.26, -3.93),
    "LFW": ("Lomé–Tokoin International", "Lomé", "Togo", 6.17, 1.25),
    "COO": ("Cadjehoun", "Cotonou", "Benin", 6.36, 2.38),
    "OUA": ("Thomas Sankara International", "Ouagadougou", "Burkina Faso", 12.35, -1.51),
    "BKO": ("Modibo Keita International", "Bamako", "Mali", 12.53, -7.95),
    "DSS": ("Blaise Diagne International", "Dakar", "Senegal", 14.67, -17.07),
    "CKY": ("Ahmed Sékou Touré International", "Conakry", "Guinea", 9.58, -13.61),
    "FNA": ("Lungi International", "Freetown", "Sierra Leone", 8.62, -13.20),
    "ROB": ("Roberts International", "Monrovia", "Liberia", 6.23, -10.36),
    "BJL": ("Banjul International", "Banjul", "Gambia", 13.34, -16.65),
    # --- North Africa
    "CAI": ("Cairo International", "Cairo", "Egypt", 30.12, 31.41),
    "HRG": ("Hurghada International", "Hurghada", "Egypt", 27.18, 33.80),
    "SSH": ("Sharm El Sheikh International", "Sharm El Sheikh", "Egypt", 27.98, 34.39),
    "ALG": ("Houari Boumediene", "Algiers", "Algeria", 36.69, 3.22),
    "TUN": ("Tunis–Carthage International", "Tunis", "Tunisia", 36.85, 10.23),
    "CMN": ("Mohammed V International", "Casablanca", "Morocco", 33.37, -7.59),
    "RAK": ("Marrakesh Menara", "Marrakesh", "Morocco", 31.61, -8.03),
    "TIP": ("Tripoli International", "Tripoli", "Libya", 32.66, 13.16),
    # --- Europe
    "LHR": ("Heathrow", "London", "United Kingdom", 51.47, -0.45),
    "LGW": ("Gatwick", "London", "United Kingdom", 51.15, -0.19),
    "MAN": ("Manchester", "Manchester", "United Kingdom", 53.35, -2.28),
    "EDI": ("Edinburgh", "Edinburgh", "United Kingdom", 55.95, -3.37),
    "DUB": ("Dublin", "Dublin", "Ireland", 53.43, -6.24),
    "CDG": ("Charles de Gaulle", "Paris", "France", 49.01, 2.55),
    "ORY": ("Orly", "Paris", "France", 48.73, 2.36),
    "AMS": ("Schiphol", "Amsterdam", "Netherlands", 52.31, 4.76),
    "BRU": ("Brussels", "Brussels", "Belgium", 50.90, 4.48),
    "FRA": ("Frankfurt", "Frankfurt", "Germany", 50.03, 8.55),
    "MUC": ("Munich", "Munich", "Germany", 48.35, 11.79),
    "BER": ("Berlin Brandenburg", "Berlin", "Germany", 52.36, 13.50),
    "ZRH": ("Zürich", "Zürich", "Switzerland", 47.46, 8.55),
    "GVA": ("Geneva", "Geneva", "Switzerland", 46.24, 6.11),
    "VIE": ("Vienna International", "Vienna", "Austria", 48.11, 16.57),
    "PRG": ("Václav Havel", "Prague", "Czechia", 50.10, 14.26),
    "WAW": ("Warsaw Chopin", "Warsaw", "Poland", 52.17, 20.97),
    "CPH": ("Copenhagen", "Copenhagen", "Denmark", 55.62, 12.65),
    "ARN": ("Stockholm Arlanda", "Stockholm", "Sweden", 59.65, 17.92),
    "OSL": ("Oslo Gardermoen", "Oslo", "Norway", 60.19, 11.10),
    "HEL": ("Helsinki-Vantaa", "Helsinki", "Finland", 60.32, 24.96),
    "MAD": ("Adolfo Suárez Madrid–Barajas", "Madrid", "Spain", 40.47, -3.57),
    "BCN": ("Josep Tarradellas Barcelona–El Prat", "Barcelona", "Spain", 41.30, 2.08),
    "LIS": ("Humberto Delgado", "Lisbon", "Portugal", 38.77, -9.13),
    "FCO": ("Leonardo da Vinci–Fiumicino", "Rome", "Italy", 41.80, 12.24),
    "MXP": ("Milan Malpensa", "Milan", "Italy", 45.63, 8.72),
    "ATH": ("Athens International", "Athens", "Greece", 37.94, 23.94),
    "IST": ("Istanbul", "Istanbul", "Türkiye", 41.26, 28.74),
    # --- Middle East
    "DXB": ("Dubai International", "Dubai", "United Arab Emirates", 25.25, 55.36),
    "AUH": ("Zayed International", "Abu Dhabi", "United Arab Emirates", 24.43, 54.65),
    "DOH": ("Hamad International", "Doha", "Qatar", 25.27, 51.61),
    "JED": ("King Abdulaziz International", "Jeddah", "Saudi Arabia", 21.68, 39.16),
    "RUH": ("King Khalid International", "Riyadh", "Saudi Arabia", 24.96, 46.70),
    "TLV": ("Ben Gurion", "Tel Aviv", "Israel", 32.01, 34.89),
    "AMM": ("Queen Alia International", "Amman", "Jordan", 31.72, 35.99),
    # --- Asia
    "BOM": ("Chhatrapati Shivaji Maharaj International", "Mumbai", "India", 19.09, 72.87),
    "DEL": ("Indira Gandhi International", "Delhi", "India", 28.56, 77.10),
    "BLR": ("Kempegowda International", "Bengaluru", "India", 13.20, 77.71),
    "CMB": ("Bandaranaike International", "Colombo", "Sri Lanka", 7.18, 79.88),
    "SIN": ("Changi", "Singapore", "Singapore", 1.36, 103.99),
    "KUL": ("Kuala Lumpur International", "Kuala Lumpur", "Malaysia", 2.75, 101.71),
    "BKK": ("Suvarnabhumi", "Bangkok", "Thailand", 13.68, 100.75),
    "CGK": ("Soekarno–Hatta International", "Jakarta", "Indonesia", -6.13, 106.66),
    "MNL": ("Ninoy Aquino International", "Manila", "Philippines", 14.51, 121.02),
    "HKG": ("Hong Kong International", "Hong Kong", "Hong Kong", 22.31, 113.91),
    "PVG": ("Shanghai Pudong International", "Shanghai", "China", 31.14, 121.81),
    "PEK": ("Beijing Capital International", "Beijing", "China", 40.08, 116.58),
    "CAN": ("Guangzhou Baiyun International", "Guangzhou", "China", 23.39, 113.30),
    "NRT": ("Narita International", "Tokyo", "Japan", 35.77, 140.39),
    "HND": ("Haneda", "Tokyo", "Japan", 35.55, 139.78),
    "ICN": ("Incheon International", "Seoul", "South Korea", 37.46, 126.44),
    # --- Oceania
    "SYD": ("Sydney Kingsford Smith", "Sydney", "Australia", -33.95, 151.18),
    "MEL": ("Melbourne", "Melbourne", "Australia", -37.67, 144.84),
    "BNE": ("Brisbane", "Brisbane", "Australia", -27.38, 153.12),
    "PER": ("Perth", "Perth", "Australia", -31.94, 115.97),
    "AKL": ("Auckland", "Auckland", "New Zealand", -37.01, 174.79),
    # --- Americas
    "JFK": ("John F. Kennedy International", "New York", "United States", 40.64, -73.78),
    "EWR": ("Newark Liberty International", "New York/Newark", "United States", 40.69, -74.17),
    "IAD": ("Washington Dulles International", "Washington DC", "United States", 38.95, -77.46),
    "ATL": ("Hartsfield–Jackson Atlanta International", "Atlanta", "United States", 33.64, -84.43),
    "MIA": ("Miami International", "Miami", "United States", 25.79, -80.29),
    "ORD": ("O'Hare International", "Chicago", "United States", 41.97, -87.90),
    "DFW": ("Dallas/Fort Worth International", "Dallas", "United States", 32.90, -97.04),
    "DEN": ("Denver International", "Denver", "United States", 39.86, -104.67),
    "LAX": ("Los Angeles International", "Los Angeles", "United States", 33.94, -118.41),
    "SFO": ("San Francisco International", "San Francisco", "United States", 37.62, -122.38),
    "SEA": ("Seattle–Tacoma International", "Seattle", "United States", 47.45, -122.31),
    "YYZ": ("Toronto Pearson International", "Toronto", "Canada", 43.68, -79.63),
    "YVR": ("Vancouver International", "Vancouver", "Canada", 49.19, -123.18),
    "MEX": ("Benito Juárez International", "Mexico City", "Mexico", 19.44, -99.07),
    "GRU": ("São Paulo/Guarulhos International", "São Paulo", "Brazil", -23.43, -46.47),
    "GIG": ("Rio de Janeiro/Galeão International", "Rio de Janeiro", "Brazil", -22.81, -43.25),
    "EZE": ("Ministro Pistarini International", "Buenos Aires", "Argentina", -34.82, -58.54),
    "SCL": ("Arturo Merino Benítez International", "Santiago", "Chile", -33.39, -70.79),
    "LIM": ("Jorge Chávez International", "Lima", "Peru", -12.02, -77.11),
    "BOG": ("El Dorado International", "Bogotá", "Colombia", 4.70, -74.14),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_airport(code):
    """Return the airport record for an IATA code, or None."""
    if not code:
        return None
    return AIRPORTS.get(str(code).strip().upper())


def resolve_airport(text):
    """Resolve free text (IATA code or city/airport name) to an IATA code.

    Returns the code or None. Used by the AI-chat path where users type
    'Cape Town' instead of 'CPT'.
    """
    if not text:
        return None
    t = str(text).strip()
    if t.upper() in AIRPORTS:
        return t.upper()
    tl = t.lower()
    # exact city match first, then substring match on city or airport name
    for code, (name, city, country, _lat, _lon) in AIRPORTS.items():
        if tl == city.lower():
            return code
    for code, (name, city, country, _lat, _lon) in AIRPORTS.items():
        if tl in city.lower() or tl in name.lower():
            return code
    return None


def route_distance_km(dep_code, arr_code):
    """Great-circle distance between two airports, or None if unknown."""
    a, b = get_airport(dep_code), get_airport(arr_code)
    if not a or not b:
        return None
    return haversine_km(a[3], a[4], b[3], b[4])


def same_country(dep_code, arr_code):
    """True when both airports are in the same country (short-haul proxy)."""
    a, b = get_airport(dep_code), get_airport(arr_code)
    if not a or not b:
        return False
    return a[2] == b[2]


def airport_options():
    """Sorted list of 'CODE — City, Country (Airport name)' display strings
    for select boxes; South African airports first."""
    sa, rest = [], []
    for code, (name, city, country, _lat, _lon) in AIRPORTS.items():
        label = f"{code} — {city}, {country} ({name})"
        (sa if country == "South Africa" else rest).append(label)
    return sorted(sa) + sorted(rest)


def code_from_option(option):
    """Extract the IATA code from an airport_options() display string."""
    return option.split(" — ")[0].strip() if option else None

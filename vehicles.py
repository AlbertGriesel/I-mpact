"""
Vehicle database for the South African market.

The app determines fuel type and fuel economy automatically from
make + model whenever possible (spec §10.2); asking users for L/100km is the
fallback (calc doc §6.2). Figures are approximate manufacturer combined-cycle
values — good enough for a footprint estimate, and clearly labelled as
approximate in the UI.

fuel: "petrol" | "diesel" | "electric"
l_per_100km applies to petrol/diesel; kwh_per_km applies to electric.
"""

VEHICLES = [
    # --- Toyota
    {"make": "Toyota", "model": "Hilux 2.4 GD-6", "fuel": "diesel", "l_per_100km": 7.9},
    {"make": "Toyota", "model": "Hilux 2.8 GD-6", "fuel": "diesel", "l_per_100km": 8.0},
    {"make": "Toyota", "model": "Corolla", "fuel": "petrol", "l_per_100km": 6.5},
    {"make": "Toyota", "model": "Corolla Cross", "fuel": "petrol", "l_per_100km": 6.8},
    {"make": "Toyota", "model": "Corolla Cross Hybrid", "fuel": "petrol", "l_per_100km": 4.3},
    {"make": "Toyota", "model": "Corolla Quest", "fuel": "petrol", "l_per_100km": 6.6},
    {"make": "Toyota", "model": "Fortuner", "fuel": "diesel", "l_per_100km": 8.0},
    {"make": "Toyota", "model": "Quantum", "fuel": "diesel", "l_per_100km": 9.5},
    {"make": "Toyota", "model": "Hiace", "fuel": "diesel", "l_per_100km": 9.5},
    {"make": "Toyota", "model": "Starlet", "fuel": "petrol", "l_per_100km": 5.4},
    {"make": "Toyota", "model": "Urban Cruiser", "fuel": "petrol", "l_per_100km": 5.8},
    {"make": "Toyota", "model": "RAV4", "fuel": "petrol", "l_per_100km": 7.0},
    {"make": "Toyota", "model": "Land Cruiser 79", "fuel": "diesel", "l_per_100km": 11.5},
    {"make": "Toyota", "model": "Land Cruiser Prado", "fuel": "diesel", "l_per_100km": 8.9},
    {"make": "Toyota", "model": "Etios", "fuel": "petrol", "l_per_100km": 5.9},
    {"make": "Toyota", "model": "Yaris", "fuel": "petrol", "l_per_100km": 5.8},
    {"make": "Toyota", "model": "Avanza", "fuel": "petrol", "l_per_100km": 6.6},
    {"make": "Toyota", "model": "Rumion", "fuel": "petrol", "l_per_100km": 6.0},
    {"make": "Toyota", "model": "Vitz", "fuel": "petrol", "l_per_100km": 5.2},
    # --- Volkswagen
    {"make": "Volkswagen", "model": "Polo Vivo", "fuel": "petrol", "l_per_100km": 5.7},
    {"make": "Volkswagen", "model": "Polo", "fuel": "petrol", "l_per_100km": 5.3},
    {"make": "Volkswagen", "model": "Polo Sedan", "fuel": "petrol", "l_per_100km": 5.5},
    {"make": "Volkswagen", "model": "Golf", "fuel": "petrol", "l_per_100km": 5.6},
    {"make": "Volkswagen", "model": "Golf GTI", "fuel": "petrol", "l_per_100km": 7.0},
    {"make": "Volkswagen", "model": "T-Cross", "fuel": "petrol", "l_per_100km": 5.5},
    {"make": "Volkswagen", "model": "T-Roc", "fuel": "petrol", "l_per_100km": 6.3},
    {"make": "Volkswagen", "model": "Tiguan", "fuel": "petrol", "l_per_100km": 7.3},
    {"make": "Volkswagen", "model": "Amarok", "fuel": "diesel", "l_per_100km": 8.7},
    {"make": "Volkswagen", "model": "Caddy", "fuel": "diesel", "l_per_100km": 6.3},
    # --- Ford
    {"make": "Ford", "model": "Ranger 2.0", "fuel": "diesel", "l_per_100km": 7.5},
    {"make": "Ford", "model": "Ranger 3.0 V6", "fuel": "diesel", "l_per_100km": 8.9},
    {"make": "Ford", "model": "EcoSport", "fuel": "petrol", "l_per_100km": 6.3},
    {"make": "Ford", "model": "Fiesta", "fuel": "petrol", "l_per_100km": 5.4},
    {"make": "Ford", "model": "Figo", "fuel": "petrol", "l_per_100km": 5.7},
    {"make": "Ford", "model": "Everest", "fuel": "diesel", "l_per_100km": 8.5},
    {"make": "Ford", "model": "Territory", "fuel": "petrol", "l_per_100km": 7.0},
    # --- Suzuki
    {"make": "Suzuki", "model": "Swift", "fuel": "petrol", "l_per_100km": 4.9},
    {"make": "Suzuki", "model": "S-Presso", "fuel": "petrol", "l_per_100km": 4.9},
    {"make": "Suzuki", "model": "Baleno", "fuel": "petrol", "l_per_100km": 5.4},
    {"make": "Suzuki", "model": "Celerio", "fuel": "petrol", "l_per_100km": 4.7},
    {"make": "Suzuki", "model": "Ertiga", "fuel": "petrol", "l_per_100km": 6.2},
    {"make": "Suzuki", "model": "Jimny", "fuel": "petrol", "l_per_100km": 6.8},
    {"make": "Suzuki", "model": "Fronx", "fuel": "petrol", "l_per_100km": 5.5},
    {"make": "Suzuki", "model": "Grand Vitara", "fuel": "petrol", "l_per_100km": 6.1},
    # --- Hyundai
    {"make": "Hyundai", "model": "Grand i10", "fuel": "petrol", "l_per_100km": 5.9},
    {"make": "Hyundai", "model": "i20", "fuel": "petrol", "l_per_100km": 6.2},
    {"make": "Hyundai", "model": "Venue", "fuel": "petrol", "l_per_100km": 6.9},
    {"make": "Hyundai", "model": "Creta", "fuel": "petrol", "l_per_100km": 7.2},
    {"make": "Hyundai", "model": "Tucson", "fuel": "petrol", "l_per_100km": 7.5},
    {"make": "Hyundai", "model": "Exter", "fuel": "petrol", "l_per_100km": 5.6},
    # --- Kia
    {"make": "Kia", "model": "Picanto", "fuel": "petrol", "l_per_100km": 5.6},
    {"make": "Kia", "model": "Rio", "fuel": "petrol", "l_per_100km": 6.2},
    {"make": "Kia", "model": "Sonet", "fuel": "petrol", "l_per_100km": 6.5},
    {"make": "Kia", "model": "Seltos", "fuel": "petrol", "l_per_100km": 6.8},
    {"make": "Kia", "model": "Sportage", "fuel": "petrol", "l_per_100km": 7.4},
    # --- Nissan
    {"make": "Nissan", "model": "NP200", "fuel": "petrol", "l_per_100km": 7.8},
    {"make": "Nissan", "model": "Navara", "fuel": "diesel", "l_per_100km": 8.1},
    {"make": "Nissan", "model": "Magnite", "fuel": "petrol", "l_per_100km": 6.0},
    {"make": "Nissan", "model": "Qashqai", "fuel": "petrol", "l_per_100km": 6.9},
    {"make": "Nissan", "model": "Almera", "fuel": "petrol", "l_per_100km": 6.3},
    # --- Renault
    {"make": "Renault", "model": "Kwid", "fuel": "petrol", "l_per_100km": 4.7},
    {"make": "Renault", "model": "Triber", "fuel": "petrol", "l_per_100km": 5.5},
    {"make": "Renault", "model": "Kiger", "fuel": "petrol", "l_per_100km": 5.6},
    {"make": "Renault", "model": "Duster", "fuel": "diesel", "l_per_100km": 5.4},
    {"make": "Renault", "model": "Clio", "fuel": "petrol", "l_per_100km": 5.6},
    {"make": "Renault", "model": "Captur", "fuel": "petrol", "l_per_100km": 6.4},
    # --- GWM / Haval
    {"make": "Haval", "model": "Jolion", "fuel": "petrol", "l_per_100km": 7.5},
    {"make": "Haval", "model": "Jolion HEV", "fuel": "petrol", "l_per_100km": 5.2},
    {"make": "Haval", "model": "H6", "fuel": "petrol", "l_per_100km": 8.0},
    {"make": "GWM", "model": "P-Series", "fuel": "diesel", "l_per_100km": 9.0},
    {"make": "GWM", "model": "Steed", "fuel": "diesel", "l_per_100km": 9.5},
    {"make": "GWM", "model": "Ora 03", "fuel": "electric", "kwh_per_km": 0.16},
    # --- Isuzu
    {"make": "Isuzu", "model": "D-Max", "fuel": "diesel", "l_per_100km": 7.8},
    {"make": "Isuzu", "model": "MU-X", "fuel": "diesel", "l_per_100km": 8.0},
    # --- Chery / Omoda
    {"make": "Chery", "model": "Tiggo 4 Pro", "fuel": "petrol", "l_per_100km": 7.0},
    {"make": "Chery", "model": "Tiggo 7 Pro", "fuel": "petrol", "l_per_100km": 7.5},
    {"make": "Omoda", "model": "C5", "fuel": "petrol", "l_per_100km": 7.0},
    # --- Mahindra
    {"make": "Mahindra", "model": "Scorpio Pik Up", "fuel": "diesel", "l_per_100km": 8.5},
    {"make": "Mahindra", "model": "XUV 3XO", "fuel": "petrol", "l_per_100km": 6.5},
    {"make": "Mahindra", "model": "Bolero", "fuel": "diesel", "l_per_100km": 8.6},
    # --- Premium
    {"make": "BMW", "model": "118i", "fuel": "petrol", "l_per_100km": 6.1},
    {"make": "BMW", "model": "320i", "fuel": "petrol", "l_per_100km": 6.5},
    {"make": "BMW", "model": "X3", "fuel": "petrol", "l_per_100km": 7.8},
    {"make": "BMW", "model": "iX1", "fuel": "electric", "kwh_per_km": 0.17},
    {"make": "Mercedes-Benz", "model": "A200", "fuel": "petrol", "l_per_100km": 6.4},
    {"make": "Mercedes-Benz", "model": "C200", "fuel": "petrol", "l_per_100km": 6.9},
    {"make": "Mercedes-Benz", "model": "GLC", "fuel": "petrol", "l_per_100km": 7.9},
    {"make": "Audi", "model": "A3", "fuel": "petrol", "l_per_100km": 5.9},
    {"make": "Audi", "model": "A4", "fuel": "petrol", "l_per_100km": 6.4},
    {"make": "Audi", "model": "Q3", "fuel": "petrol", "l_per_100km": 7.2},
    {"make": "Volvo", "model": "XC40 Recharge", "fuel": "electric", "kwh_per_km": 0.20},
    {"make": "Mini", "model": "Cooper SE", "fuel": "electric", "kwh_per_km": 0.15},
    # --- EVs
    {"make": "BYD", "model": "Atto 3", "fuel": "electric", "kwh_per_km": 0.16},
    {"make": "BYD", "model": "Dolphin", "fuel": "electric", "kwh_per_km": 0.14},
    {"make": "Volkswagen", "model": "ID.4", "fuel": "electric", "kwh_per_km": 0.18},
]


def _norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum() or ch.isspace()).strip()


def lookup_vehicle(make, model, year=None):
    """Best-effort match of make + model against the database.

    Returns the vehicle record or None. Year is accepted for the schema but
    combined-cycle figures vary little across the years we cover, so it does
    not change the match.
    """
    if not make and not model:
        return None
    nmake, nmodel = _norm(make), _norm(model)
    candidates = [v for v in VEHICLES if nmake and nmake in _norm(v["make"])]
    if not candidates and nmodel:
        candidates = VEHICLES[:]  # allow model-only matches ("Polo Vivo")
    best, best_score = None, 0
    for v in candidates:
        vmodel = _norm(v["model"])
        tokens = [t for t in nmodel.split() if t]
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in vmodel)
        vhits = sum(1 for t in vmodel.split() if t in nmodel)
        score = hits * 2 + vhits
        # exact model string beats everything
        if vmodel == nmodel:
            score += 100
        if score > best_score and (hits > 0 or vmodel == nmodel):
            best, best_score = v, score
    return best


def vehicle_makes():
    return sorted({v["make"] for v in VEHICLES})

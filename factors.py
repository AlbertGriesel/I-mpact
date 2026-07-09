"""
Conversion factors and fixed assumptions for the deterministic calculation
engine.

Every factor is stored with its source, geography, unit and a confidence tag
so calculations can be audited and updated (spec §18 "Calculation
Philosophy"). Values follow "Environmental Impact Tracker Calculation
Information" (the calculation reference document).

Tags:
  measured   – official published figure for the right geography
  proxy      – official figure from another geography (mostly UK Gov 2026 GHG
               conversion factors) used as a stand-in
  assumption – [MVP assumption] from the calculation document
"""

FACTORS = {
    # ------------------------------------------------------------------ water
    "water_national_l_person_day": {
        "value": 218.0, "unit": "L/person/day",
        "source": "South African government per-capita benchmark",
        "geography": "South Africa", "tag": "measured",
    },
    "shower_l_per_minute": {
        "value": 8.0, "unit": "L/minute",
        "source": "Eskom residential calculator shower-flow assumption",
        "geography": "South Africa", "tag": "measured",
    },
    # Optional water-carbon proxies — NOT added to the headline footprint.
    "water_supply_kgco2e_per_m3": {
        "value": 0.1913, "unit": "kg CO2e/m3",
        "source": "UK Government 2026 GHG conversion factors",
        "geography": "UK proxy", "tag": "proxy",
    },
    "water_treatment_kgco2e_per_m3": {
        "value": 0.17088, "unit": "kg CO2e/m3",
        "source": "UK Government 2026 GHG conversion factors",
        "geography": "UK proxy", "tag": "proxy",
    },
    "water_combined_kgco2e_per_m3": {
        "value": 0.36218, "unit": "kg CO2e/m3",
        "source": "UK Government 2026 GHG conversion factors (simplified)",
        "geography": "UK proxy", "tag": "proxy",
    },

    # ------------------------------------------------------------ electricity
    "sa_grid_kgco2e_per_kwh": {
        "value": 0.906, "unit": "kg CO2e/kWh",
        "source": "South African 2023 national grid emission factor report "
                  "(0.906 tCO2e/MWh)",
        "geography": "South Africa", "tag": "measured",
    },
    "base_load_kwh_month": {
        "value": 150.0, "unit": "kWh/month",
        "source": "[MVP assumption] unmeasured household base load "
                  "(refrigeration, lighting, electronics)",
        "geography": "generic", "tag": "assumption",
    },
    "stove_plate_kw": {
        "value": 1.5, "unit": "kW",
        "source": "[MVP assumption] default active stove plate rating",
        "geography": "generic", "tag": "assumption",
    },
    "oven_kw": {
        "value": 2.5, "unit": "kW",
        "source": "[MVP assumption] default oven rating",
        "geography": "generic", "tag": "assumption",
    },
    "geyser_kw": {
        "value": 3.0, "unit": "kW",
        "source": "[MVP assumption] typical SA electric geyser element",
        "geography": "South Africa", "tag": "assumption",
    },
    "days_per_month": {
        "value": 30.42, "unit": "days",
        "source": "365 / 12", "geography": "generic", "tag": "measured",
    },

    # ---------------------------------------------------------- fuels (proxy)
    "petrol_kgco2e_per_l": {
        "value": 2.35372, "unit": "kg CO2e/L",
        "source": "UK Government 2026 GHG conversion factors (combustion)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "diesel_kgco2e_per_l": {
        "value": 2.66155, "unit": "kg CO2e/L",
        "source": "UK Government 2026 GHG conversion factors (100% mineral)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "lpg_kgco2e_per_l": {
        "value": 1.55713, "unit": "kg CO2e/L",
        "source": "UK Government 2026 GHG conversion factors",
        "geography": "UK proxy", "tag": "proxy",
    },
    "natural_gas_kgco2e_per_m3": {
        "value": 2.04987, "unit": "kg CO2e/m3",
        "source": "UK Government 2026 GHG conversion factors (100% mineral)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "paraffin_kgco2e_per_l": {
        "value": 2.54016, "unit": "kg CO2e/L",
        "source": "UK Government 2026 GHG conversion factors (burning oil)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "coal_kgco2e_per_kg": {
        "value": 2.90495, "unit": "kg CO2e/kg",
        "source": "UK Government 2026 GHG conversion factors (domestic coal)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "generator_l_per_hour_fallback": {
        "value": 1.5, "unit": "L/hour",
        "source": "[MVP assumption] rough generator consumption fallback",
        "geography": "generic", "tag": "assumption",
    },

    # ------------------------------------------------------ public transport
    "pt_bus_kgco2e_per_pkm": {
        "value": 0.12552, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (bus)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_local_bus_kgco2e_per_pkm": {
        "value": 0.10151, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (average local bus)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_coach_kgco2e_per_pkm": {
        "value": 0.03948, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (coach)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_train_kgco2e_per_pkm": {
        "value": 0.03092, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (national rail)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_light_rail_kgco2e_per_pkm": {
        "value": 0.02121, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (light rail/tram)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_taxi_kgco2e_per_pkm": {
        "value": 0.14861, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 GHG conversion factors (taxi)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "pt_minibus_taxi_kgco2e_per_pkm": {
        "value": 0.12552, "unit": "kg CO2e/passenger-km",
        "source": "[Temporary proxy] UK bus factor used for SA minibus taxis",
        "geography": "UK proxy", "tag": "assumption",
    },

    # ---------------------------------------------------------------- flights
    # Published factors already include the 8% distance uplift — do not add it.
    "flight_short_economy": {
        "value": 0.12576, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (domestic)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "flight_short_business": {
        "value": 0.18863, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (domestic)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "flight_intl_economy": {
        "value": 0.10916, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (intl non-UK)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "flight_intl_premium": {
        "value": 0.17465, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (intl non-UK)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "flight_intl_business": {
        "value": 0.31656, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (intl non-UK)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "flight_intl_first": {
        "value": 0.43663, "unit": "kg CO2e/passenger-km",
        "source": "UK Government 2026 flight conversion tables (intl non-UK)",
        "geography": "UK proxy", "tag": "proxy",
    },

    # ------------------------------------------------------------------- diet
    # Peer-reviewed UK diet study standardised to 2,000 kcal/day.
    "diet_heavy_meat_kg_day": {
        "value": 7.19, "unit": "kg CO2e/day",
        "source": "UK dietary study (high meat)", "geography": "UK proxy",
        "tag": "proxy",
    },
    "diet_average_kg_day": {
        "value": 5.63, "unit": "kg CO2e/day",
        "source": "UK dietary study (medium meat)", "geography": "UK proxy",
        "tag": "proxy",
    },
    "diet_chicken_kg_day": {
        "value": 4.67, "unit": "kg CO2e/day",
        "source": "[Proxy mapping] UK dietary study low-meat category",
        "geography": "UK proxy", "tag": "proxy",
    },
    "diet_pescatarian_kg_day": {
        "value": 3.91, "unit": "kg CO2e/day",
        "source": "UK dietary study (fish-eater)", "geography": "UK proxy",
        "tag": "proxy",
    },
    "diet_vegetarian_kg_day": {
        "value": 3.81, "unit": "kg CO2e/day",
        "source": "UK dietary study (vegetarian)", "geography": "UK proxy",
        "tag": "proxy",
    },
    "diet_vegan_kg_day": {
        "value": 2.89, "unit": "kg CO2e/day",
        "source": "UK dietary study (vegan)", "geography": "UK proxy",
        "tag": "proxy",
    },

    # ------------------------------------------------- business operations
    # Used only by the business assessment path (calculate_fleet / _waste).
    # Personal footprints never touch these.
    "waste_mixed_landfill_kgco2e_per_kg": {
        "value": 0.45867, "unit": "kg CO2e/kg",
        "source": "UK Government 2026 GHG conversion factors "
                  "(commercial & industrial waste to landfill)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "waste_recycling_kgco2e_per_kg": {
        "value": 0.02107, "unit": "kg CO2e/kg",
        "source": "UK Government 2026 GHG conversion factors "
                  "(mixed recycling, open-loop)",
        "geography": "UK proxy", "tag": "proxy",
    },
    "fleet_default_kgco2e_per_km": {
        "value": 0.20, "unit": "kg CO2e/km",
        "source": "[MVP assumption] fallback for a fleet vehicle whose fuel "
                  "economy is unknown (mixed car / light-commercial average)",
        "geography": "generic", "tag": "assumption",
    },
}

# Diet category label -> factor key
DIET_FACTOR_KEYS = {
    "Heavy meat eater": "diet_heavy_meat_kg_day",
    "Average diet": "diet_average_kg_day",
    "Mostly chicken": "diet_chicken_kg_day",
    "Pescatarian": "diet_pescatarian_kg_day",
    "Vegetarian": "diet_vegetarian_kg_day",
    "Vegan": "diet_vegan_kg_day",
}

# Food-waste option -> fraction of purchased food wasted.
# 0.03 and 0.35 are [MVP assumptions] per the calculation document.
FOOD_WASTE_FRACTIONS = {
    "None": 0.00,
    "Very little": 0.03,
    "Around 10%": 0.10,
    "Around 20%": 0.20,
    "More than 30%": 0.35,
}

# Shopping habit -> qualitative intensity score ([MVP assumptions]).
# Sent to the LLM as context; never converted into CO2e in the MVP.
SHOPPING_INTENSITY = {
    "Much less": 0.60,
    "Less": 0.80,
    "Average": 1.00,
    "More": 1.25,
    "Much more": 1.50,
}

# Public transport option (as shown in the UI) -> factor key
PUBLIC_TRANSPORT_FACTOR_KEYS = {
    "Bus": "pt_bus_kgco2e_per_pkm",
    "Train": "pt_train_kgco2e_per_pkm",
    "Minibus taxi / taxi": "pt_minibus_taxi_kgco2e_per_pkm",
    "Subway": "pt_light_rail_kgco2e_per_pkm",   # light-rail proxy
    "Other": "pt_local_bus_kgco2e_per_pkm",     # generic local-bus proxy
}


def F(key):
    """Return the numeric value of a factor."""
    return FACTORS[key]["value"]


def factor_info(key):
    """Return the full factor record (value, unit, source, geography, tag)."""
    return FACTORS[key]

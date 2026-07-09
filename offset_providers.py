"""
Carbon-offset provider directory (spec §7).

IMPORTANT — honesty rules baked into this file:
  * These are real, independently-verifiable organisations. We claim no
    partnership, endorsement or commission (there is none).
  * `standard` states only what is publicly true about each organisation
    (e.g. Gold Standard IS itself a certification standard). We do not invent
    certifications for anyone.
  * This is a maintainable config: edit / add / remove entries here as the
    market changes. `active: False` hides an entry without deleting it.
  * If you cannot verify a provider's current status, set `active: False`
    rather than showing something unverified.

Each entry:
  name, url, blurb, project_types (list), regions, standard (verification note),
  active (bool).
"""

PROVIDERS = [
    {
        "name": "Gold Standard",
        "url": "https://www.goldstandard.org",
        "blurb": "A leading certification standard and marketplace for carbon "
                 "and sustainable-development projects, founded by WWF and "
                 "other NGOs.",
        "project_types": ["Renewable energy", "Clean cookstoves",
                           "Community & water projects"],
        "regions": "Global (many projects in Africa)",
        "standard": "Is itself the Gold Standard for the Global Goals "
                    "certification.",
        "active": True,
    },
    {
        "name": "Verra (Verified Carbon Standard)",
        "url": "https://verra.org",
        "blurb": "Operates the VCS Program, the world's most widely used "
                 "voluntary greenhouse-gas crediting programme, with a public "
                 "project registry.",
        "project_types": ["Forest conservation (REDD+)", "Renewable energy",
                           "Improved land management"],
        "regions": "Global",
        "standard": "Runs the Verified Carbon Standard (VCS) registry.",
        "active": True,
    },
    {
        "name": "Credible Carbon",
        "url": "https://www.crediblecarbon.com",
        "blurb": "A South African carbon registry focused on pro-poor projects "
                 "that keep verification and money transparent and local.",
        "project_types": ["Community energy", "Restoration", "Waste & biogas"],
        "regions": "South Africa / Southern Africa",
        "standard": "Independent South African registry with public project "
                    "records.",
        "active": True,
    },
    {
        "name": "Food & Trees for Africa",
        "url": "https://trees.org.za",
        "blurb": "A long-running South African NGO running tree-planting and "
                 "food-garden programmes with a carbon-offset stream.",
        "project_types": ["Tree planting", "Urban greening", "Food gardens"],
        "regions": "South Africa",
        "standard": "Established SA non-profit; review current project "
                    "verification on their site.",
        "active": True,
    },
    {
        "name": "myclimate",
        "url": "https://www.myclimate.org",
        "blurb": "A Swiss non-profit foundation offering vetted international "
                 "offset projects and footprint tools.",
        "project_types": ["Renewable energy", "Efficient cookstoves",
                           "Reforestation"],
        "regions": "Global",
        "standard": "Projects largely certified to Gold Standard / Plan Vivo.",
        "active": True,
    },
    {
        "name": "Cool Effect",
        "url": "https://www.cooleffect.org",
        "blurb": "A US non-profit marketplace that publishes detailed project "
                 "documentation and how each rand/dollar is used.",
        "project_types": ["Cookstoves", "Forest protection", "Biogas"],
        "regions": "Global",
        "standard": "Lists third-party standards (e.g. Gold Standard, VCS) per "
                    "project.",
        "active": True,
    },
]


def active_providers():
    """The providers to display, in config order (skips active: False)."""
    return [p for p in PROVIDERS if p.get("active", True)]

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR]:
    path.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.nature.com/search"
SEARCH_QUERY = "oer"  
YEAR_RANGE = "2015-2025"
MAX_PAGES = 5 


# serve de uma implementação para evitar os bloqueios
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.5

# Limite de armazenamento local
STORAGE_LIMIT_MB = 500

METADATA_CSV = RAW_DIR / "articles_metadata.csv"

KEY_TERMS = [

    # --- 🧭 Termos gerais sobre OER ---
    "overpotential", "electrocatalyst", "substrate",
    "OER", "oxygen evolution reaction",
    "morphology", "structure",
    "acidic", "alkaline", "neutral", "electrolyte", "pH",

    # --- ⚗️ Elementos químicos comuns em catalisadores ---
    # (usados como metais ativos ou dopantes)
    "Ni", "Co", "Fe", "Mn", "Cu", "Zn", "Mo", "W", "V", "Cr",
    "Ru", "Ir", "Pt", "Pd", "Sn", "Pb", "Ti", "Nb", "Ta", "Zr",
    "Ce", "La", "Sr", "Ba",

    # --- 🧱 Classes de compostos típicos ---
    # (sufixos e tipos de materiais usados em OER)
    "oxide", "hydroxide", "sulfide", "phosphide",
    "nitride", "carbide",
    "perovskite", "spinel", "amorphous",

    # --- ⚙️ Exemplos específicos (frequentes em artigos) ---
    "MoS2", "NiFe-LDH", "Co3O4", "NiO", "Fe2O3",
    "NiCo2O4", "NiMoO4", "NiFe2O4", "CoOOH", "Ni(OH)2",

    # --- 💎 Estruturas e morfologias ---
    "nanorods", "nanosheets", "nanowires", "nanoparticles",
    "nanoflakes", "nanotubes", "porous", "hollow", "core-shell",

    # --- 🔩 Substratos e suportes condutores ---
    "nickel foam", "carbon cloth", "graphene", "ITO", "FTO",
    "copper foil", "stainless steel", "carbon paper", "CNT", "carbon nanotube",

    # --- 💧 Condições químicas e eletrólitos ---
    "KOH", "NaOH", "H2SO4", "HCl", "H3PO4", "Na2CO3",
    "LiOH", "NH4Cl", "phosphate buffer", "electrolyte",

    # --- 📏 Termos de desempenho ---
    "current density", "Tafel slope", "exchange current", "stability",
    "onset potential", "performance", "activity"
]
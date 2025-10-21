from pathlib import Path

# Configuração de paths - considerando que o script é executado do diretório project/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Criar diretórios se não existirem
for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR]:
    path.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.nature.com/search"
SEARCH_QUERY = "oer"  
YEAR_RANGE = "2015-2025"
MAX_PAGES = 5

# Configurações para evitar bloqueios
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.5
STORAGE_LIMIT_MB = 500
METADATA_CSV = RAW_DIR / "articles_metadata.csv"
PARSED_CSV = PROCESSED_DIR / "articles_parsed.csv"

KEY_TERMS = [
    "overpotential", "electrocatalyst", "substrate", "OER", "oxygen evolution reaction",
    "morphology", "structure", "acidic", "alkaline", "neutral", "electrolyte", "pH",
    "Ni", "Co", "Fe", "Mn", "Cu", "Zn", "Mo", "W", "V", "Cr", "Ru", "Ir", "Pt", "Pd", 
    "Sn", "Pb", "Ti", "Nb", "Ta", "Zr", "Ce", "La", "Sr", "Ba", "oxide", "hydroxide", 
    "sulfide", "phosphide", "nitride", "carbide", "perovskite", "spinel", "amorphous",
    "MoS2", "NiFe-LDH", "Co3O4", "NiO", "Fe2O3", "NiCo2O4", "NiMoO4", "NiFe2O4", 
    "CoOOH", "Ni(OH)2", "nanorods", "nanosheets", "nanowires", "nanoparticles",
    "nanoflakes", "nanotubes", "porous", "hollow", "core-shell", "nickel foam", 
    "carbon cloth", "graphene", "ITO", "FTO", "copper foil", "stainless steel", 
    "carbon paper", "CNT", "carbon nanotube", "KOH", "NaOH", "H2SO4", "HCl", "H3PO4", 
    "Na2CO3", "LiOH", "NH4Cl", "phosphate buffer", "electrolyte", "current density", 
    "Tafel slope", "exchange current", "stability", "onset potential", "performance", 
    "activity"
]
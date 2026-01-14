from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# Criar diretórios se não existirem
for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR, LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

PDF_DIR = RAW_DIR / "pdf"
PARSED_DATA_CSV = PROCESSED_DIR / "catalyst_data.csv"
METADATA_CSV = PROCESSED_DIR / "articles_parsed.csv"

REQUEST_DELAY = 1.5
STORAGE_LIMIT_MB = 500

PDF_BATCH_SIZE = 50  # Número de PDFs para processar de uma vez
MIN_TEXT_LENGTH = 200  # Tamanho mínimo do texto extraído do PDF

BASE_URL = "https://www.nature.com/search"
SEARCH_QUERY = "oer"  
YEAR_RANGE = "2015-2025"
MAX_PAGES = 1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}



# CATEGORIAS PARA FEATURE ENGINEERING (ML)
PATTERNS = {
    'overpotential': [  # Padrões para sobrepotencial
        r'overpotential\s*[=:]\s*(\d+\.?\d*)\s*(?:mV|V)',
        r'η\s*[=:]\s*(\d+\.?\d*)\s*(?:mV|V)',
        r'(\d+\.?\d*)\s*(?:mV|V)\s*overpotential',
        r'overpotential\s*of\s*(\d+\.?\d*)\s*(?:mV|V)'
    ],
    'electrolyte': [  # Padrões para eletrólito
        r'(?:\d+\.?\d*\s*M\s+)?([A-Za-z0-9\s\-]+)(?:\s+solution|\s+electrolyte)',
        r'in\s+([\d\.]+\s*M\s*[A-Za-z0-9\s\-]+)',
        r'([A-Za-z0-9\s\-]+)\s+(?:aqueous\s+)?solution'
    ]
}

# Listas de palavras-chave para identificação
CATALYST_KEYWORDS = [
    # Elementos
    "Ni", "Co", "Fe", "Mn", "Cu", "Zn", "Mo", "W", "V", "Cr",
    "Ru", "Ir", "Pt", "Pd", "Sn", "Pb", "Ti", "Nb", "Ta", "Zr",
    "Ce", "La", "Sr", "Ba",
    # Compostos comuns
    "MoS2", "NiFe-LDH", "Co3O4", "NiO", "Fe2O3", "NiCo2O4", 
    "NiMoO4", "NiFe2O4", "CoOOH", "Ni(OH)2",
    # Tipos de materiais
    "perovskite", "spinel", "LDH", "layered double hydroxide"
]

ELEMENTS = CATALYST_KEYWORDS[:24]  # Primeiros 24 são elementos
COMPOUNDS = CATALYST_KEYWORDS[24:34]  # Próximos 10 são compostos
MATERIAL_TYPES = CATALYST_KEYWORDS[34:]  # Últimos são tipos de materiais

SUBSTRATE_KEYWORDS = [
    "nickel foam", "carbon cloth", "carbon paper", "glassy carbon", 
    "GC", "FTO", "ITO", "copper foam", "titanium foil",
    "stainless steel", "graphene", "CNT", "carbon nanotube"
]

ELECTROLYTE_KEYWORDS = [
    "KOH", "NaOH", "H2SO4", "HCl", "H3PO4", "Na2CO3",
    "LiOH", "NH4Cl", "phosphate buffer", "PBS", "seawater"
]

# Padrões para encontrar catalisador no texto
CATALYST_PATTERNS = [
    r'(?:catalyst|electrocatalyst|material)[\s\S]{0,150}?([A-Za-z0-9\s\-/]+?)(?:was|is|shows|exhibits|\.|,)',
    r'([A-Za-z0-9\s\-/]+)(?:\s+based\s+catalyst|\s+electrocatalyst)'
]

# Padrões para encontrar substrato no texto
SUBSTRATE_PATTERNS = [
    r'(?:on|deposited on|supported on)\s+([a-zA-Z0-9\s\-]+?)(?:substrate|electrode|foam|paper|cloth)',
    r'substrate[:\s]+([a-zA-Z0-9\s\-]+)'
]

# Para compatibilidade
KEY_TERMS = CATALYST_KEYWORDS + SUBSTRATE_KEYWORDS + ELECTROLYTE_KEYWORDS
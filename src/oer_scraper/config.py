from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR, LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

PDF_DIR = RAW_DIR / "pdf"

PARSED_DATA_CSV = PROCESSED_DIR / "catalyst_data.csv"
METADATA_CSV = PROCESSED_DIR / "articles_parsed.csv"

REQUEST_DELAY = 2
STORAGE_LIMIT_MB = 2000

PDF_BATCH_SIZE = 50
MIN_TEXT_LENGTH = 1000

BASE_URL = "https://www.nature.com/search"
SEARCH_QUERY = '"oxygen evolution reaction" OR "OER"'
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

# Parâmetros de busca e janela
WINDOW_SIZE = 1000  # Tamanho da janela em caracteres

# Palavras-chave para filtrar a janela
KEYWORDS_FILTER = [
    "overpotential", "η", "mv", "v vs", "rhe", "current density", "ma cm", "ma/cm"
]

# Evidências de tensão (usadas para validar se a janela é realmente um dado)
VOLTAGE_EVIDENCE = ["mv", "v vs", "overpotential", "η"]
from __future__ import annotations
import logging
import time
import shutil
from pathlib import Path
from typing import Optional, Any
import requests
from bs4 import BeautifulSoup
import pandas as pd

# IMPORTA config (assume que config.py está ao lado em oer_scraper)
from src.oer_scraper import config

def setup_logger(name: str = "oer_scraper", log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # evita adicionar handlers duplicados em import múltiplo

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s — %(levelname)s — %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_file:
        # cria a pasta pra mim
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger

LOGGER = setup_logger(log_file=Path("logs/oer_scraper.log"))

def get_folder_size_mb(path: Path) -> float:
    """
    Retorna o tamanho da pasta (recursivamente) em megabytes (MB).
    """
    path = Path(path)
    total = 0
    if not path.exists():
        return 0.0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                # ignora arquivos inacessíveis
                continue
    return total / (1024 * 1024)

def check_storage_limit(path: Path, limit_mb: Optional[float] = None) -> bool:
    """
    Verifica se a pasta excede o limite (em MB).
    - path: pasta a checar (ex: config.RAW_DIR)
    - limit_mb: limite em MB (se None usa config.STORAGE_LIMIT_MB)
    Retorna True se dentro do limite, False se excedeu.
    """
    if limit_mb is None:
        limit_mb = config.STORAGE_LIMIT_MB
    size = get_folder_size_mb(path)
    LOGGER.info("Tamanho da pasta %s: %.2f MB (limite: %.2f MB)", path, size, limit_mb)
    return size <= float(limit_mb)

def save_dataframe_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    """
    Salva DataFrame em CSV.
    - df: pandas.DataFrame
    - path: caminho do CSV
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8")
    LOGGER.info("CSV salvo: %s (linhas: %d)", path, len(df))

def write_text_file(path: Path, content: str, overwrite: bool = True) -> None:
    """
    Salva texto em arquivo (para salvar HTML baixado).
    - overwrite: se False e arquivo existir, não sobrescreve.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        LOGGER.debug("Arquivo existe e overwrite=False: %s", path)
        return
    path.write_text(content, encoding="utf-8")
    LOGGER.debug("Arquivo escrito: %s", path)

def safe_request(url: str, headers: Optional[dict] = None, timeout: int = 15) -> Optional[requests.Response]:
    """
    Faz GET com tratamento básico de erros.
    - Retorna Response se status_code == 200, caso contrário None.
    - Faz logging de erros comuns.
    """
    headers = headers or config.HEADERS
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        LOGGER.warning("RequestException ao acessar %s — %s", url, exc)
        return None

    if resp.status_code == 200:
        return resp
    else:
        LOGGER.warning("Resposta não OK (%s) para %s", resp.status_code, url)
        return None

def get_soup(url: str, headers: Optional[dict] = None) -> Optional[BeautifulSoup]:
    """
    Retorna um BeautifulSoup do conteúdo HTML da URL.
    - Usa safe_request internamente.
    - Retorna None em caso de erro.
    """
    resp = safe_request(url, headers=headers)
    if not resp:
        return None
    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        soup = BeautifulSoup(resp.text, "html.parser")
    return soup

def paywall_detection(html_text: str) -> bool:
    """
    Heurística simples para detectar paywall / conteúdo bloqueado.
    Retorna True se parecer paywalled (ou seja, NÃO acessível gratuitamente),
    False se parecer acessível.
    Observação: é uma heurística — pode falhar; serve para evitar baixar PDFs inúteis.
    """
    lowered = html_text.lower()
    # padrões comuns
    pay_phrases = [
        "purchase", "access denied", "sign in", "sign in to", "subscribe", "buy",
        "institutional access", "you do not have access", "purchase article", "login"
    ]
    # se encontrar uma das frases, assume paywall
    for ph in pay_phrases:
        if ph in lowered:
            LOGGER.debug("Indicador de paywall detectado: %s", ph)
            return True

    # indicativo contrário: se tem 'download pdf' ou 'supplementary' e 'pdf' é provável aberto
    if ("download pdf" in lowered) or ("supplementary information" in lowered) or ("pdf" in lowered and "download" in lowered):
        return False

    # default: assumir acessível (mais permissivo)
    return False

def download_html_if_allowed(url: str, year: str, journal: str, doi: str, overwrite: bool = False, headers: Optional[dict] = None) -> Optional[Path]:
    """
    Baixa o HTML da URL e salva em data/raw/html/{year}/{journal}/{doi}.html.
    Retorna o Path salvo, ou None se paywalled/erro.
    """
    headers = headers or config.HEADERS
    safe_name = safe_filename_from_doi(doi)
    dest = config.RAW_DIR / "html" / str(year) / journal.replace("/", "_") / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not overwrite:
        LOGGER.debug("HTML já existe e overwrite=False: %s", dest)
        return dest

    resp = safe_request(url, headers=headers)
    if not resp:
        LOGGER.warning("Falha ao obter URL: %s", url)
        return None

    html = resp.text
    if paywall_detection(html):
        LOGGER.info("Conteúdo paywalled, não salvo: %s", url)
        return None

    write_text_file(dest, html, overwrite=overwrite)
    LOGGER.info("HTML salvo: %s", dest)
    return dest

def wait_request_delay(seconds: Optional[float] = None) -> None:
    """
    Espera o tempo configurado entre requisições.
    - Usa config.REQUEST_DELAY por padrão.
    """
    secs = seconds if seconds is not None else config.REQUEST_DELAY
    LOGGER.debug("Aguardando %.2f segundos (delay entre requisições).", secs)
    time.sleep(secs)

def ensure_path(path: Path) -> Path:
    """
    Garante que o diretório existe e retorna o Path absoluto.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def safe_filename_from_doi(doi: str) -> str:
    """
    Converte DOI em um nome de arquivo seguro (substitui / e espaços).
    Ex: 10.1038/s41467-021-12345-z -> 10.1038_s41467-021-12345-z.html
    """
    safe = doi.replace("/", "_").replace(":", "_").strip()
    return f"{safe}.html"


# ---------------------------
# Exemplo de função de alto nível para salvar metadados (usada pelo scraper)
# ---------------------------
def save_metadata_dataframe(df: pd.DataFrame) -> None:
    """
    Salva o CSV de metadados no caminho configurado em config.METADATA_CSV
    e faz log do resultado.
    """
    cfg_path = Path(config.METADATA_CSV)
    save_dataframe_csv(df, cfg_path)
from pathlib import Path
import pandas as pd
import re
from bs4 import BeautifulSoup
from oer_scraper.utils import LOGGER, write_text_file
from oer_scraper import config
import spacy

# --- Inicializar NLP ---
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


def extract_text_from_html(html_path: Path) -> str:
    """
    Lê o HTML e retorna o texto principal do artigo.
    """
    html_path = Path(html_path)
    if not html_path.exists():
        LOGGER.warning("HTML não encontrado: %s", html_path)
        return ""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # extrair texto relevante do artigo (ex: tags <p>)
    paragraphs = soup.find_all("p")
    text = " ".join([p.get_text(separator=" ", strip=True) for p in paragraphs])
    return text


def extract_overpotential(text: str) -> str:
    """
    Extrai sobrepotencial do texto usando regex.
    Ex: '280 mV @ 10 mA cm−2'
    """
    pattern = r"(\d+\.?\d*)\s*mV(?:\s*@\s*(\d+\.?\d*)\s*mA\s*cm[\-−]?\d*)?"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(0)
    return ""


def extract_key_terms(text: str, terms: list[str]) -> dict:
    """
    Procura por termos-chave do config.KEY_TERMS no texto.
    Retorna dicionário term->primeiro match encontrado.
    """
    result = {}
    lowered = text.lower()
    for term in terms:
        if term.lower() in lowered:
            # simples: retorna o termo encontrado
            result[term] = term
    return result


def extract_entities_with_nlp(text: str) -> dict:
    """
    Usa spaCy para extrair entidades químicas / materiais.
    """
    doc = nlp(text)
    entities = {"materials": [], "conditions": []}
    for ent in doc.ents:
        # Exemplo: categorizar entidades por tipo
        if ent.label_ in ["CHEMICAL", "MATERIAL", "ORG"]:
            entities["materials"].append(ent.text)
        else:
            entities["conditions"].append(ent.text)
    # remover duplicatas
    entities["materials"] = list(set(entities["materials"]))
    entities["conditions"] = list(set(entities["conditions"]))
    return entities


def parse_article_html(html_path: Path) -> dict:
    """
    Parser principal para um HTML de artigo.
    Retorna dicionário com os campos técnicos.
    """
    text = extract_text_from_html(html_path)
    if not text:
        return {}

    data = {}
    data["overpotential"] = extract_overpotential(text)
    data.update(extract_key_terms(text, config.KEY_TERMS))
    data.update(extract_entities_with_nlp(text))
    return data


def parse_all_articles(metadata_csv: Path, output_csv: Path) -> None:
    """
    Itera sobre todos os artigos do CSV de metadados,
    aplica parser técnico e salva CSV final.
    """
    df_meta = pd.read_csv(metadata_csv)
    all_data = []

    for idx, row in df_meta.iterrows():
        html_path = Path(row.get("html_path", ""))
        if not html_path.exists():
            LOGGER.warning("HTML não encontrado para DOI %s", row.get("doi"))
            continue

        technical_data = parse_article_html(html_path)

        # combinar metadados + extração técnica
        combined = {**row.to_dict(), **technical_data}
        all_data.append(combined)
        LOGGER.info("Processado artigo %d/%d: %s", idx+1, len(df_meta), row.get("doi"))

    if all_data:
        df_final = pd.DataFrame(all_data)
        df_final.to_csv(output_csv, index=False, encoding="utf-8")
        LOGGER.info("Parser finalizado. CSV técnico salvo: %s", output_csv)
    else:
        LOGGER.info("Nenhum artigo processado pelo parser.")

from pathlib import Path
import logging
from src.oer_scraper import config
from src.oer_scraper.utils import LOGGER
from src.oer_scraper.scraper_nature import scrape_articles_metadata_and_html
from src.oer_scraper.parser_html import parse_all_articles

def run_oer_pipeline():
    """
    Pipeline completo:
    1. Scraper: coleta metadados e baixa HTML dos artigos gratuitos.
    2. Parser: extrai dados técnicos de HTML e salva CSV final.
    """
    LOGGER.info("=== INÍCIO DA PIPELINE OER ===")

    # --- 1. Scraper ---
    LOGGER.info("Etapa 1: scraping de metadados e download de HTML")
    scrape_articles_metadata_and_html(max_pages=config.MAX_PAGES)

    # --- 2. Parser técnico ---
    LOGGER.info("Etapa 2: parsing de HTML para dados técnicos")
    metadata_csv = Path(config.METADATA_CSV)
    output_csv = Path(config.PROCESSED_DIR) / "oer_articles.csv"
    parse_all_articles(metadata_csv, output_csv)

    LOGGER.info("=== PIPELINE OER FINALIZADA ===")
    LOGGER.info("CSV final salvo em: %s", output_csv)


if __name__ == "__main__":
    run_oer_pipeline()

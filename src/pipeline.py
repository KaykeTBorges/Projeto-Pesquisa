import pandas as pd
from pathlib import Path

from oer_scraper.scraper import Scraper
from oer_scraper.parser import Parser
from oer_scraper.config import PARSED_DATA_CSV
from oer_scraper.logger import get_pipeline_logger

logger = get_pipeline_logger()


def main():
    """
    Pipeline completo:
    Nature → PDFs → Parser → CSV
    """

    logger.info("Iniciando pipeline completo")

    scraper = Scraper()
    parser = Parser()

    csv_path = Path(PARSED_DATA_CSV)
    csv_exists = csv_path.exists()

    articles = scraper.search_articles()

    for article in articles:
        pdf_url = scraper.get_pdf_url(article["article_url"])
        if not pdf_url:
            continue

        safe_title = article["title"].replace(" ", "_").replace("/", "")
        pdf_path = scraper.pdf_dir / f"{safe_title}.pdf"

        # 1. Baixar PDF
        success = scraper.download_pdf(pdf_url, pdf_path.name)
        if not success:
            continue

        # 2. Parsear imediatamente
        parsed = parser.parse_pdf(pdf_path)
        if not parsed:
            continue

        # 3. Salvar incrementalmente no CSV
        df = pd.DataFrame([parsed])

        df.to_csv(
            csv_path,
            mode="a",
            index=False,
            header=not csv_exists
        )

        csv_exists = True  # depois da primeira escrita

        logger.info(f"Registro salvo no CSV: {parsed['pdf_name']}")

    logger.info("Pipeline streaming finalizado")



if __name__ == "__main__":
    main()
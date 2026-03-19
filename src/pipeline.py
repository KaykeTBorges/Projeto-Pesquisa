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
    Nature (Busca) -> Download (DOI-based) -> Parsing (Sliding Window + AI) -> CSV (Incremental)
    """

    logger.info("Iniciando pipeline OER...")

    scraper = Scraper()
    parser = Parser()
    csv_path = Path(PARSED_DATA_CSV)
    
    # Busca lista de artigos (sem baixar ainda)
    articles = scraper.search_articles()
    logger.info(f"Total de {len(articles)} artigos identificados para processamento.")

    for article in articles:
        try:
            # 1. Download usando a lógica otimizada (DOI-based)
            # O download_pdf agora retorna True/False e gerencia o nome interno
            filename = scraper._sanitize_filename(article["title"])
            pdf_path = scraper.pdf_dir / filename
            
            if not scraper.download_pdf(article):
                continue
                
            # 2. Parsing usando a lógica de Janelas Deslizantes
            # O parse_pdf retorna uma lista de dicionários (pode ter + de 1 dado por PDF)
            parsed_data_list = parser.parse_pdf(pdf_path)
            
            if not parsed_data_list:
                logger.warning(f"Nenhum dado extraído de: {filename}")
                continue

            # 3. Salvar incrementalmente no CSV
            df = pd.DataFrame(parsed_data_list)
            
            file_exists = csv_path.exists()
            df.to_csv(
                csv_path,
                mode="a",
                index=False,
                header=not file_exists,
                encoding="utf-8"
            )

            logger.info(f"Sucesso! {len(parsed_data_list)} registros salvos de: {filename}")

        except Exception as e:
            logger.error(f"Falha no processamento do artigo {article.get('title')}: {e}")
            continue

    logger.info("Pipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()
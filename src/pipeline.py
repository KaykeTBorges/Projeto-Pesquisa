import pandas as pd
from pathlib import Path
from oer_scraper.scraper import Scraper
from oer_scraper.parser import Parser
from oer_scraper.config import PARSED_DATA_CSV
from oer_scraper.logger import get_pipeline_logger

logger = get_pipeline_logger()

def load_processed_pdfs(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    try:
        df = pd.read_csv(csv_path)
        if "source_pdf" in df.columns:
            return set(df["source_pdf"].dropna().unique())
    except Exception as e:
        logger.error(f"Erro ao ler CSV existente: {e}")
    return set()

def main():
    """
    Pipeline completo:
    Nature (Busca) -> Download (DOI-based) -> Parsing (Sliding Window + AI) -> CSV (Incremental)
    """

    logger.info("Iniciando pipeline OER...")

    scraper = Scraper()
    parser = Parser()
    csv_path = Path(PARSED_DATA_CSV)
    
    processed_pdfs = load_processed_pdfs(csv_path)
    
    # 0. Processar PDFs locais que ainda não foram processados (antes do scraper)
    logger.info("Verificando PDFs locais já baixados e não processados...")
    local_pdfs = list(scraper.pdf_dir.glob("*.pdf"))
    
    for pdf_path in local_pdfs:
        filename = pdf_path.name
        if filename in processed_pdfs:
            continue
            
        logger.info(f"Processando PDF local pendente: {filename}")
        try:
            parsed_data_list = parser.parse_pdf(pdf_path)
            
            if not parsed_data_list:
                logger.warning(f"Nenhum dado extraído de: {filename}")
                processed_pdfs.add(filename)
                continue

            df = pd.DataFrame(parsed_data_list)
            file_exists = csv_path.exists()
            df.to_csv(
                csv_path,
                mode="a",
                index=False,
                header=not file_exists,
                encoding="utf-8"
            )

            processed_pdfs.add(filename)
            logger.info(f"Sucesso! {len(parsed_data_list)} registros salvos de: {filename}")

        except Exception as e:
            logger.error(f"Falha no processamento do arquivo {filename}: {e}")
    
    # Busca lista de artigos (sem baixar ainda)
    articles = scraper.search_articles()
    logger.info(f"Total de {len(articles)} artigos identificados para processamento.")

    for article in articles:
        try:
            filename = scraper._sanitize_filename(article["title"])
            
            # Verifica se já está processado ANTES de tentar ler
            if filename in processed_pdfs:
                logger.info(f"Artigo já processado anteriormente, ignorando: {filename}")
                continue
                
            pdf_path = scraper.pdf_dir / filename
            
            # 1. Download usando a lógica otimizada (DOI-based)
            # O download_pdf agora retorna True/False e evita requisições se arquivo existir
            if not scraper.download_pdf(article):
                continue
                
            # 2. Parsing usando a lógica de Janelas Deslizantes
            # O parse_pdf retorna uma lista de dicionários (pode ter + de 1 dado por PDF)
            parsed_data_list = parser.parse_pdf(pdf_path)
            
            if not parsed_data_list:
                logger.warning(f"Nenhum dado extraído de: {filename}")
                processed_pdfs.add(filename)
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

            processed_pdfs.add(filename)
            logger.info(f"Sucesso! {len(parsed_data_list)} registros salvos de: {filename}")

        except Exception as e:
            logger.error(f"Falha no processamento do artigo {article.get('title')}: {e}")
            continue

    logger.info("Pipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()
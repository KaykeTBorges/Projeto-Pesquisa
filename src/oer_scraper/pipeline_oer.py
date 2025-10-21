import logging
import time
import pandas as pd
import argparse
import sys
from pathlib import Path

# Importar módulos do mesmo pacote
from . import config
from .scraper_nature_requests import NatureRequestsScraper
from .parser_html import NatureHTMLParser

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.BASE_DIR / 'pipeline.log'),
        logging.StreamHandler()
    ]
)

def check_existing_data():
    """Verificar dados existentes"""
    try:
        html_files = list(config.RAW_DIR.glob("*.html"))
        metadata_exists = config.METADATA_CSV.exists()
        
        if metadata_exists:
            df = pd.read_csv(config.METADATA_CSV)
            with_html = df[df['html_path'].notna() & (df['html_path'] != '')]
            logging.info(f"📊 Dados existentes:")
            logging.info(f"   - CSV: {len(df)} artigos")
            logging.info(f"   - HTMLs: {len(html_files)} arquivos")
            logging.info(f"   - Com HTML: {len(with_html)} artigos")
            return len(df), len(html_files), len(with_html)
        else:
            logging.info("📊 Nenhum dado existente")
            return 0, 0, 0
            
    except Exception as e:
        logging.error(f"Erro ao verificar dados: {e}")
        return 0, 0, 0

def run_scraping_phase():
    """Executar fase de scraping"""
    try:
        logging.info("📥 Iniciando scraping com requests...")
        scraper = NatureRequestsScraper()
        scraper.run()
        
        if config.METADATA_CSV.exists():
            df = pd.read_csv(config.METADATA_CSV)
            success_count = len(df[df['html_path'].notna() & (df['html_path'] != '')])
            logging.info(f"✅ Scraping concluído: {success_count} artigos")
            return True, success_count
        else:
            logging.warning("⚠️  Scraping concluído mas sem CSV")
            return False, 0
            
    except Exception as e:
        logging.error(f"❌ Erro no scraping: {e}")
        return False, 0

def run_parsing_phase():
    """Executar fase de parsing"""
    try:
        logging.info("🔍 Iniciando fase de parsing...")
        parser = NatureHTMLParser()
        result_df = parser.process_all_articles()
        
        if not result_df.empty:
            overpotential_count = result_df['overpotential_mv'].notna().sum()
            oer_mentions = (result_df['oer_mentions'] > 0).sum() if 'oer_mentions' in result_df.columns else 0
            
            logging.info(f"✅ Parsing concluído: {len(result_df)} artigos")
            logging.info(f"   - Com overpotential: {overpotential_count}")
            logging.info(f"   - Que mencionam OER: {oer_mentions}")
            return True, len(result_df)
        else:
            logging.warning("⚠️  Parsing sem resultados")
            return False, 0
            
    except Exception as e:
        logging.error(f"❌ Erro no parsing: {e}")
        return False, 0

def run_complete_pipeline(force_scraping=False):
    """Executar pipeline completa"""
    logging.info("🚀 INICIANDO PIPELINE COMPLETA OER")
    logging.info("=" * 50)
    
    existing_articles, existing_htmls, existing_with_html = check_existing_data()
    
    scraping_success = False
    scraping_count = 0
    
    if force_scraping or existing_with_html == 0:
        logging.info("📥 FASE 1: SCRAPING")
        scraping_success, scraping_count = run_scraping_phase()
    else:
        logging.info(f"📥 FASE 1: SCRAPING (pulando - {existing_with_html} artigos existentes)")
        scraping_success = True
        scraping_count = existing_with_html
    
    if not scraping_success:
        logging.error("❌ Pipeline interrompida - falha no scraping")
        return False
    
    time.sleep(2)
    
    logging.info("🔍 FASE 2: PARSING")
    parsing_success, parsing_count = run_parsing_phase()
    
    if not parsing_success:
        logging.error("❌ Pipeline com falha no parsing")
        return False
    
    logging.info("=" * 50)
    logging.info("🎉 PIPELINE CONCLUÍDA!")
    logging.info(f"   📊 Artigos processados: {parsing_count}")
    logging.info(f"   💾 Dados em: {config.PARSED_CSV}")
    logging.info("=" * 50)
    
    return True

def run_parsing_only():
    """Executar apenas o parsing"""
    logging.info("🔍 EXECUTANDO APENAS PARSING")
    success, count = run_parsing_phase()
    
    if success:
        logging.info(f"✅ Parsing concluído: {count} artigos processados")
    else:
        logging.error("❌ Parsing falhou")
    
    return success

def run_scraping_only():
    """Executar apenas o scraping"""
    logging.info("📥 EXECUTANDO APENAS SCRAPING")
    success, count = run_scraping_phase()
    
    if success:
        logging.info(f"✅ Scraping concluído: {count} artigos com HTML baixado")
    else:
        logging.error("❌ Scraping falhou")
    
    return success

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Pipeline OER - Scraping e Parsing da Nature')
    parser.add_argument('--scraping-only', action='store_true', help='Apenas scraping')
    parser.add_argument('--parsing-only', action='store_true', help='Apenas parsing')
    parser.add_argument('--force-scraping', action='store_true', help='Forçar novo scraping')
    
    args = parser.parse_args()
    
    try:
        if args.scraping_only:
            run_scraping_only()
        elif args.parsing_only:
            run_parsing_only()
        else:
            run_complete_pipeline(force_scraping=args.force_scraping)
            
    except KeyboardInterrupt:
        logging.info("⏹️  Interrompido pelo usuário")
    except Exception as e:
        logging.error(f"💥 Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
import time
import pandas as pd
import argparse
import sys
from pathlib import Path

# Importar módulos do mesmo pacote
from . import config
from .scraper_ml_ready import MLReadyScraper
from .parser_ml_ready import MLReadyParser
from .logger import get_pipeline_logger, get_ml_logger

# Configurar logger
logger = get_pipeline_logger()
ml_logger = get_ml_logger()

def run_ml_pipeline():
    """Executar pipeline otimizada para ML"""
    ml_logger.info("🚀 INICIANDO PIPELINE ML-READY")
    ml_logger.info("=" * 60)
    
    try:
        scraper = MLReadyScraper()
        scraper.run()
        
        ml_logger.info("🎉 PIPELINE ML CONCLUÍDA!")
        ml_logger.info("   📈 Dados prontos para: Random Forest, XGBoost, SVR, etc.")
        ml_logger.info(f"   💾 Arquivo: {config.METADATA_CSV}")
        
    except Exception as e:
        ml_logger.error(f"❌ Erro na pipeline: {e}")
        raise

def run_parsing_only():
    """Executar apenas o parsing dos HTMLs existentes"""
    ml_logger.info("🔍 INICIANDO PARSING DOS HTMLs EXISTENTES")
    
    try:
        parser = MLReadyParser()
        
        # Processar todos os HTMLs existentes
        html_files = list(config.RAW_DIR.glob("*.html"))
        ml_logger.info(f"Encontrados {len(html_files)} HTMLs para processar")
        
        all_data = []
        for i, html_file in enumerate(html_files):
            # Tentar extrair URL do arquivo ou usar placeholder
            url = f"https://www.nature.com/articles/{html_file.stem}"
            article_data = parser.parse_single_article(html_file, url)
            if article_data:
                all_data.append(article_data)
            
            # Log de progresso
            if (i + 1) % 10 == 0:
                ml_logger.info(f"Processados {i + 1}/{len(html_files)} HTMLs")
        
        # Salvar resultados
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Garantir tipos de dados consistentes para ML
            df = ensure_ml_data_types(df)
            
            df.to_csv(config.METADATA_CSV, index=False)
            ml_logger.info(f"✅ Parsing concluído: {len(df)} artigos salvos")
            
            # Análise dos resultados
            analyze_results(df)
        else:
            ml_logger.warning("Nenhum dado processado")
            
    except Exception as e:
        ml_logger.error(f"❌ Erro no parsing: {e}")
        raise

def ensure_ml_data_types(df):
    """Garantir tipos de dados consistentes para ML"""
    # Colunas numéricas
    numeric_cols = ['overpotential_mv', 'current_density', 'ph_value', 
                   'temperature_c', 'stability_hours', 'tafel_slope',
                   'faradaic_efficiency', 'turnover_frequency']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Colunas de contagem
    count_cols = [col for col in df.columns if col.startswith('element_')]
    for col in count_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def analyze_results(df):
    """Analisar resultados do parsing"""
    ml_logger.info("📊 ANÁLISE DOS RESULTADOS:")
    ml_logger.info(f"   📈 Total de artigos processados: {len(df)}")
    
    # Estatísticas de features numéricas
    numeric_features = ['overpotential_mv', 'current_density', 'ph_value']
    for feature in numeric_features:
        if feature in df.columns:
            non_null = df[feature].notna().sum()
            if non_null > 0:
                mean_val = df[feature].mean()
                ml_logger.info(f"   🔢 {feature}: {non_null} valores (média: {mean_val:.2f})")
    
    # Estatísticas de elementos
    element_cols = [col for col in df.columns if col.startswith('element_')]
    if element_cols:
        element_counts = df[element_cols].sum().sort_values(ascending=False)
        top_elements = element_counts.head(5)
        ml_logger.info(f"   ⚗️  Elementos mais comuns: {dict(top_elements)}")
    
    # Estatísticas de compostos
    compound_cols = [col for col in df.columns if col.startswith('compound_')]
    if compound_cols:
        compound_counts = df[compound_cols].sum().sort_values(ascending=False)
        top_compounds = compound_counts.head(5)
        ml_logger.info(f"   🧪 Compostos mais comuns: {dict(top_compounds)}")
    
    # Estatísticas de materiais
    material_cols = [col for col in df.columns if col.startswith('material_')]
    if material_cols:
        material_counts = df[material_cols].sum().sort_values(ascending=False)
        top_materials = material_counts.head(5)
        ml_logger.info(f"   🏗️  Materiais mais comuns: {dict(top_materials)}")

def analyze_ml_features():
    """Analisar features extraídas para ML"""
    if not config.METADATA_CSV.exists():
        ml_logger.error("Arquivo de dados não encontrado")
        return
    
    df = pd.read_csv(config.METADATA_CSV)
    
    ml_logger.info("🔍 ANÁLISE DE FEATURES PARA ML:")
    ml_logger.info(f"   📊 Total de amostras: {len(df)}")
    ml_logger.info(f"   🎯 Total de features: {len(df.columns)}")
    
    # Análise por categoria
    categories = {
        'Elementos': [col for col in df.columns if col.startswith('element_')],
        'Compostos': [col for col in df.columns if col.startswith('compound_')],
        'Materiais': [col for col in df.columns if col.startswith('material_')],
        'Morfologias': [col for col in df.columns if col.startswith('morphology_')],
        'Substratos': [col for col in df.columns if col.startswith('substrate_')],
        'Numéricas': ['overpotential_mv', 'current_density', 'ph_value', 'tafel_slope', 'faradaic_efficiency']
    }
    
    for category, features in categories.items():
        if features:
            available_features = [f for f in features if f in df.columns]
            if available_features:
                non_null_count = sum(df[available_features].notna().any(axis=1))
                ml_logger.info(f"   📁 {category}: {len(available_features)} features ({non_null_count} amostras com dados)")

def run_scraping_only():
    """Executar apenas o scraping (sem parsing em tempo real)"""
    ml_logger.info("📥 INICIANDO APENAS SCRAPING")
    
    try:
        # Usar o MLReadyScraper mas modificar para não processar em tempo real
        # Para isso, vamos criar uma versão simplificada temporária
        ml_logger.info("⚠️  Modo scraping-only não disponível no momento")
        ml_logger.info("💡 Use 'python run.py' para pipeline completa")
        ml_logger.info("💡 Use 'python run.py --parsing-only' para processar HTMLs existentes")
        
    except Exception as e:
        ml_logger.error(f"❌ Erro no scraping: {e}")
        raise

def main():
    """Função principal para ser chamada externamente"""
    parser = argparse.ArgumentParser(description='Pipeline OER - Otimizada para ML')
    parser.add_argument('--scraping-only', action='store_true', help='Apenas scraping (sem processamento) - NÃO DISPONÍVEL')
    parser.add_argument('--parsing-only', action='store_true', help='Apenas parsing dos HTMLs existentes')
    parser.add_argument('--analyze', action='store_true', help='Apenas analisar features')
    
    args = parser.parse_args()
    
    try:
        if args.scraping_only:
            run_scraping_only()
        elif args.parsing_only:
            run_parsing_only()
        elif args.analyze:
            analyze_ml_features()
        else:
            run_ml_pipeline()
            
    except KeyboardInterrupt:
        ml_logger.info("⏹️  Execução interrompida pelo usuário")
    except Exception as e:
        ml_logger.error(f"💥 Erro fatal: {e}")
        sys.exit(1)

# Esta parte permite executar o arquivo diretamente
if __name__ == "__main__":
    main()
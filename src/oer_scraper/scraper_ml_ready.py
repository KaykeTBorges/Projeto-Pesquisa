import time
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from urllib.parse import urljoin, urlencode
import sys

# Importar configuração e parser
from . import config
from .parser_ml_ready import MLReadyParser
from .logger import get_scraper_logger

# Configurar logger
logger = get_scraper_logger()

class MLReadyScraper:
    """Scraper que processa em tempo real para dados de ML"""
    
    def __init__(self):
        self.session = requests.Session()
        self.parser = MLReadyParser()
        self.setup_session()
        self.data = []
        
    def setup_session(self):
        """Configurar sessão com headers"""
        self.session.headers.update({
            "User-Agent": config.HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
        })
        
    def random_delay(self):
        """Delay aleatório entre requisições"""
        delay = random.uniform(config.REQUEST_DELAY * 0.7, config.REQUEST_DELAY * 1.3)
        time.sleep(delay)
    
    def make_request(self, url, max_retries=3):
        """Fazer requisição com tratamento de erro e retry"""
        for attempt in range(max_retries):
            try:
                self.random_delay()
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 404]:
                    logger.warning(f"Erro {response.status_code} para {url}")
                    return None
                elif response.status_code == 429:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(f"Rate limit. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Status code {response.status_code} para {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro de requisição (tentativa {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
        
        logger.error(f"Falha após {max_retries} tentativas para {url}")
        return None
    
    def extract_article_urls_from_search(self, html_content):
        """Extrair URLs de artigos da página de busca"""
        soup = BeautifulSoup(html_content, 'lxml')
        urls = []
        
        selectors = [
            'a[data-track-action="view article"]',
            'h3 a',
            '.c-card__title a',
            'a[href*="/articles/"]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if href and '/articles/' in href:
                    full_url = f"https://www.nature.com{href}" if href.startswith('/') else href
                    if re.search(r'/articles/(\w+-\d+-\w+-\d+-\w+|\w+)', full_url):
                        if full_url not in urls:
                            urls.append(full_url)
            if urls:
                break
        
        return urls
    
    def download_and_process_article(self, url):
        """Baixar HTML e processar imediatamente"""
        try:
            # Extrair DOI para nome do arquivo
            doi_match = re.search(r'articles/([^/?]+)', url)
            doi = doi_match.group(1) if doi_match else re.sub(r'[^a-zA-Z0-9]', '_', url[-50:])
            filename = f"{doi.replace('/', '_')}.html"
            html_path = config.RAW_DIR / filename
            
            # Pular se já processado
            if self.is_already_processed(doi):
                logger.info(f"Artigo já processado: {doi}")
                return True
            
            # Baixar HTML
            logger.info(f"Baixando e processando: {url}")
            response = self.make_request(url)
            if not response:
                return False
            
            # Verificar se é página válida
            if "article" not in response.text.lower():
                logger.warning(f"Página não parece ser um artigo: {url}")
                return False
            
            # Salvar HTML
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # PROCESSAMENTO EM TEMPO REAL: Chamar parser imediatamente
            article_data = self.parser.parse_single_article(html_path, url)
            
            if article_data:
                self.data.append(article_data)
                self.save_progress()  # Salvar após cada artigo
                logger.info(f"✅ Processado: {article_data.get('title', 'Unknown')}")
                return True
            else:
                logger.warning(f"Falha no processamento: {url}")
                return False
            
        except Exception as e:
            logger.error(f"Erro ao processar {url}: {e}")
            return False
    
    def is_already_processed(self, doi):
        """Verificar se artigo já foi processado"""
        if config.METADATA_CSV.exists():
            try:
                df = pd.read_csv(config.METADATA_CSV)
                return doi in df['doi'].values
            except:
                return False
        return False
    
    def scrape_search_page(self, page_num):
        """Raspar uma página de busca"""
        params = {
            'q': config.SEARCH_QUERY,
            'date_range': config.YEAR_RANGE,
            'page': page_num
        }
        
        url = f"{config.BASE_URL}?{urlencode(params)}"
        logger.info(f"Raspando página {page_num}: {url}")
        
        response = self.make_request(url)
        if not response:
            return False
        
        urls = self.extract_article_urls_from_search(response.text)
        
        if not urls:
            logger.warning(f"Nenhum artigo encontrado na página {page_num}")
            if "no results" in response.text.lower():
                return False
            return True
        
        logger.info(f"Encontrados {len(urls)} artigos na página {page_num}")
        
        # Processar cada artigo imediatamente
        success_count = 0
        for i, article_url in enumerate(urls):
            try:
                success = self.download_and_process_article(article_url)
                if success:
                    success_count += 1
                
                # Delay entre artigos
                if i < len(urls) - 1:
                    self.random_delay()
                    
            except Exception as e:
                logger.error(f"Erro no artigo {i+1}: {e}")
                continue
        
        logger.info(f"Página {page_num}: {success_count}/{len(urls)} artigos processados")
        return success_count > 0
    
    def save_progress(self):
        """Salvar progresso - agora com dados completos de ML"""
        try:
            if self.data:
                df = pd.DataFrame(self.data)
                
                # Remover duplicatas
                if 'doi' in df.columns:
                    df = df.drop_duplicates(subset=['doi'], keep='last')
                
                # Garantir tipos de dados consistentes para ML
                df = self.ensure_ml_data_types(df)
                
                df.to_csv(config.METADATA_CSV, index=False, encoding='utf-8')
                logger.info(f"📊 Progresso salvo: {len(df)} artigos (ML-ready)")
                
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
    
    def ensure_ml_data_types(self, df):
        """Garantir tipos de dados consistentes para ML"""
        # Colunas numéricas
        numeric_cols = ['overpotential_mv', 'current_density', 'ph_value', 
                       'temperature_c', 'stability_hours', 'tafel_slope',
                       'faradaic_efficiency', 'turnover_frequency']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Colunas de contagem
        count_cols = [col for col in df.columns if col.startswith('count_')]
        for col in count_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    
    def run(self):
        """Executar scraping com processamento em tempo real"""
        try:
            logger.info("🚀 Iniciando scraping com processamento ML em tempo real")
            
            # Carregar progresso anterior
            if config.METADATA_CSV.exists():
                existing_df = pd.read_csv(config.METADATA_CSV)
                logger.info(f"📁 Progresso anterior: {len(existing_df)} artigos processados")
                self.data = existing_df.to_dict('records')
            
            # Raspar páginas
            for page_num in range(1, config.MAX_PAGES + 1):
                success = self.scrape_search_page(page_num)
                
                if not success:
                    logger.info(f"🏁 Sem mais resultados na página {page_num}")
                    break
                
                # Delay entre páginas
                if page_num < config.MAX_PAGES:
                    time.sleep(random.uniform(3, 5))
            
            # Salvar final
            self.save_progress()
            
            # Estatísticas finais
            self.print_ml_statistics()
            
            logger.info(f"🎉 Scraping ML concluído! {len(self.data)} artigos processados")
            
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            raise
    
    def print_ml_statistics(self):
        """Imprimir estatísticas para análise ML"""
        if not self.data:
            return
            
        df = pd.DataFrame(self.data)
        
        logger.info("📈 ESTATÍSTICAS PARA ML:")
        logger.info(f"   📊 Total de artigos: {len(df)}")
        
        # Estatísticas de features numéricas
        numeric_features = ['overpotential_mv', 'current_density', 'ph_value']
        for feature in numeric_features:
            if feature in df.columns:
                non_null = df[feature].notna().sum()
                if non_null > 0:
                    mean_val = df[feature].mean()
                    logger.info(f"   🔢 {feature}: {non_null} valores (média: {mean_val:.2f})")
        
        # Estatísticas de elementos
        element_cols = [col for col in df.columns if col.startswith('element_')]
        if element_cols:
            element_counts = df[element_cols].sum().sort_values(ascending=False)
            top_elements = element_counts.head(5)
            logger.info(f"   ⚗️  Elementos mais comuns: {dict(top_elements)}")
        
        # Estatísticas de compostos
        compound_cols = [col for col in df.columns if col.startswith('compound_')]
        if compound_cols:
            compound_counts = df[compound_cols].sum().sort_values(ascending=False)
            top_compounds = compound_counts.head(5)
            logger.info(f"   🧪 Compostos mais comuns: {dict(top_compounds)}")

def main():
    """Função principal"""
    try:
        scraper = MLReadyScraper()
        scraper.run()
    except Exception as e:
        logger.error(f"Erro: {e}")
        raise

if __name__ == "__main__":
    main()
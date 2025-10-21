import time
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path
import re
from urllib.parse import urljoin, urlencode
import sys

# Importar configuração do mesmo pacote
from . import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.BASE_DIR / 'scraper_requests.log'),
        logging.StreamHandler()
    ]
)

class NatureRequestsScraper:
    """Scraper para artigos OER da Nature usando requests + BeautifulSoup"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        self.data = []
        
    def setup_session(self):
        """Configurar sessão com headers"""
        self.session.headers.update({
            "User-Agent": config.HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
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
                elif response.status_code == 403:
                    logging.warning(f"Acesso negado (403) para {url}")
                    return None
                elif response.status_code == 404:
                    logging.warning(f"Página não encontrada (404) para {url}")
                    return None
                elif response.status_code == 429:
                    logging.warning(f"Rate limit (429) para {url}. Tentativa {attempt + 1}/{max_retries}")
                    time.sleep(10 * (attempt + 1))
                    continue
                else:
                    logging.warning(f"Status code {response.status_code} para {url}")
                    
            except requests.exceptions.RequestException as e:
                logging.warning(f"Erro de requisição (tentativa {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
        
        logging.error(f"Falha após {max_retries} tentativas para {url}")
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
                    if href.startswith('/'):
                        full_url = f"https://www.nature.com{href}"
                    else:
                        full_url = href
                    
                    if re.search(r'/articles/\w+-\d+-\w+-\d+-\w+', full_url) or re.search(r'/articles/\w+', full_url):
                        if full_url not in urls:
                            urls.append(full_url)
            
            if urls:
                logging.info(f"Encontradas {len(urls)} URLs usando seletor: {selector}")
                break
        
        return urls
    
    def extract_metadata_from_listing(self, html_content, url):
        """Extrair metadados básicos do listing"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        article_id = url.split('/articles/')[-1]
        article_element = None
        
        selectors = [
            f'a[href*="{article_id}"]',
            f'[data-article-id*="{article_id}"]',
            '.c-card'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                if article_id in str(elem):
                    article_element = elem
                    break
            if article_element:
                break
        
        metadata = {
            'url': url,
            'title': '',
            'authors': '',
            'year': None,
            'open_access': False,
            'doi': self.extract_doi_from_url(url)
        }
        
        if article_element:
            title_elem = article_element.select_one('h3, .c-card__title, [data-test="article-title"]')
            if title_elem:
                metadata['title'] = title_elem.get_text(strip=True)
            
            author_elems = article_element.select('[data-test="author-name"], .c-author-list__item, .app-author')
            authors = []
            for author_elem in author_elems:
                author_name = author_elem.get_text(strip=True)
                if author_name and len(author_name) > 2:
                    authors.append(author_name)
            metadata['authors'] = '; '.join(authors)
            
            date_elem = article_element.select_one('time, [datetime]')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                date_attr = date_elem.get('datetime', '')
                year_match = re.search(r'20\d{2}', date_text or date_attr)
                if year_match:
                    metadata['year'] = int(year_match.group())
            
            oa_indicators = article_element.select('.c-article-access, [data-test="open-access"], .c-card__badge')
            metadata['open_access'] = any('open' in elem.get_text().lower() for elem in oa_indicators)
        
        return metadata
    
    def extract_doi_from_url(self, url):
        """Extrair DOI da URL"""
        match = re.search(r'articles/([^/?]+)', url)
        return match.group(1) if match else ''
    
    def download_article_html(self, url):
        """Baixar HTML do artigo"""
        try:
            doi = self.extract_doi_from_url(url)
            filename = f"{doi.replace('/', '_')}.html" if doi else re.sub(r'[^a-zA-Z0-9]', '_', url[-50:]) + '.html'
            html_path = config.RAW_DIR / filename
            
            if html_path.exists():
                logging.info(f"HTML já existe: {filename}")
                return str(html_path)
            
            logging.info(f"Baixando: {url}")
            response = self.make_request(url)
            
            if not response:
                return ""
            
            if "article" not in response.text.lower() and "content" not in response.text.lower():
                logging.warning(f"Página não parece ser um artigo: {url}")
                return ""
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logging.info(f"HTML salvo: {filename}")
            return str(html_path)
            
        except Exception as e:
            logging.error(f"Erro ao baixar {url}: {e}")
            return ""
    
    def scrape_search_page(self, page_num):
        """Raspar uma página de busca"""
        params = {
            'q': config.SEARCH_QUERY,
            'date_range': config.YEAR_RANGE,
            'page': page_num
        }
        
        url = f"{config.BASE_URL}?{urlencode(params)}"
        logging.info(f"Raspando página {page_num}: {url}")
        
        response = self.make_request(url)
        if not response:
            return False
        
        urls = self.extract_article_urls_from_search(response.text)
        
        if not urls:
            logging.warning(f"Nenhum artigo encontrado na página {page_num}")
            if "no results" in response.text.lower() or "no articles" in response.text.lower():
                return False
            return True
        
        logging.info(f"Encontrados {len(urls)} artigos na página {page_num}")
        
        success_count = 0
        for i, article_url in enumerate(urls):
            try:
                logging.info(f"Processando artigo {i+1}/{len(urls)}")
                
                html_path = self.download_article_html(article_url)
                if not html_path:
                    continue
                
                metadata = self.extract_metadata_from_listing(response.text, article_url)
                metadata['html_path'] = html_path
                
                self.data.append(metadata)
                success_count += 1
                
                if success_count % 5 == 0:
                    self.save_progress()
                
            except Exception as e:
                logging.error(f"Erro no artigo {i+1}: {e}")
                continue
        
        logging.info(f"Página {page_num}: {success_count}/{len(urls)} artigos processados")
        return success_count > 0
    
    def save_progress(self):
        """Salvar progresso"""
        try:
            if self.data:
                df = pd.DataFrame(self.data)
                if 'doi' in df.columns:
                    df = df.drop_duplicates(subset=['doi'], keep='first')
                df.to_csv(config.METADATA_CSV, index=False, encoding='utf-8')
                logging.info(f"Progresso salvo: {len(df)} artigos")
        except Exception as e:
            logging.error(f"Erro ao salvar: {e}")
    
    def run(self):
        """Executar scraping"""
        try:
            logging.info("Iniciando scraping com requests")
            
            existing_dois = set()
            if config.METADATA_CSV.exists():
                existing_df = pd.read_csv(config.METADATA_CSV)
                existing_dois = set(existing_df['doi'].dropna().tolist())
                logging.info(f"Progresso anterior: {len(existing_dois)} artigos")
            
            for page_num in range(1, config.MAX_PAGES + 1):
                success = self.scrape_search_page(page_num)
                
                if not success:
                    logging.info(f"Sem mais resultados na página {page_num}")
                    break
                
                if page_num < config.MAX_PAGES:
                    time.sleep(random.uniform(3, 5))
            
            self.save_progress()
            logging.info(f"Scraping concluído! {len(self.data)} artigos")
            
        except Exception as e:
            logging.error(f"Erro no scraping: {e}")
            raise

def main():
    """Função principal para executar scraping standalone"""
    try:
        scraper = NatureRequestsScraper()
        scraper.run()
    except Exception as e:
        logging.error(f"Erro: {e}")
        raise

if __name__ == "__main__":
    main()
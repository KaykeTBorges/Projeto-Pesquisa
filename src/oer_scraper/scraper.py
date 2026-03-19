import time
import re
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from oer_scraper import config
from oer_scraper.logger import get_scraper_logger

logger = get_scraper_logger()

class Scraper:
    """Scraper robusto para Nature com controle de retentativa e unicidade de arquivos."""

    def __init__(self):
        self.base_url = config.BASE_URL
        self.search_query = config.SEARCH_QUERY
        self.max_pages = config.MAX_PAGES
        self.pdf_dir = config.PDF_DIR
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Estratégia de Retentativa: se o servidor falhar, tenta novamente
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3, 
            backoff_factor=1, 
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update(config.HEADERS)

    def _sanitize_filename(self, title: str) -> str:
        """Cria nome único baseado no título."""
        title_clean = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
        return f"{title_clean[:60]}.pdf"

    def search_articles(self) -> List[Dict[str, str]]:
        """Busca artigos na Nature e extrai URL e DOI."""
        articles = []
        for page in range(1, self.max_pages + 1):
            logger.info(f"Buscando página {page}")
            response = self.session.get(self.base_url, params={"q": self.search_query, "page": page})
            
            soup = BeautifulSoup(response.text, "html.parser")
            for item in soup.select("article.u-full-height"):
                title_tag = item.select_one("h3 a")
                if not title_tag: continue
                
                href = title_tag["href"]
                
                articles.append({
                    "title": title_tag.text.strip(),
                    "url": "https://www.nature.com" + href,
                })
            time.sleep(config.REQUEST_DELAY)
        return articles

    def download_pdf(self, article: Dict) -> bool:
        """Acessa página, encontra link e baixa o PDF."""
        resp = self.session.get(article["url"])
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Procura link de download
        pdf_tag = soup.find("a", attrs={"data-track-action": "download pdf"})
        if not pdf_tag: return False
        
        pdf_url = "https://www.nature.com" + pdf_tag["href"]
        filename = self._sanitize_filename(article["title"])
        filepath = self.pdf_dir / filename
        
        if filepath.exists(): return True

        pdf_resp = self.session.get(pdf_url, stream=True)
        with open(filepath, "wb") as f:
            for chunk in pdf_resp.iter_content(8192):
                f.write(chunk)
        
        logger.info(f"Baixado: {filename}")
        return True

    def run(self):
        """Execução robusta do pipeline."""
        articles = self.search_articles()
        for art in articles:
            try:
                if self.download_pdf(art):
                    time.sleep(config.REQUEST_DELAY)
            except Exception as e:
                logger.error(f"Erro no download {art['title']}: {e}")
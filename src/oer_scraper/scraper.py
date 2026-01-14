import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Optional

from oer_scraper import config
from oer_scraper.logger import get_scraper_logger

logger = get_scraper_logger()

class Scraper:
    """Scraper para artigos da Nature sobre OER"""

    def __init__(self):
        self.base_url = config.BASE_URL
        self.search_query = config.SEARCH_QUERY 
        self.year_range = config.YEAR_RANGE
        self.max_pages = config.MAX_PAGES
        self.headers = config.HEADERS
        self.request_delay = config.REQUEST_DELAY

        self.pdf_dir = config.PDF_DIR
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def search_articles(self) -> List[Dict[str, str]]:
        """Busca de artigos retorna os metadados"""

        articles = []

        for page in range(1, self.max_pages+1):
            params = {
                "q": self.search_query,
                "page": page,
                "date_range": self.year_range
            }

            logger.info(f"Buscando página {page} da Nature")

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                logger.warning(f"Erro na busca: status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            results = soup.select("article.u-full-height")
            logger.info(f"{len(results)} artigos encontrados na página {page}")

            for item in results:
                title_tag = item.select_one("h3 a")
                if not title_tag:
                    continue

                article_url = "https://www.nature.com" + title_tag["href"]

                articles.append({
                    "title": title_tag.text.strip(),
                    "article_url": article_url
                })

            
            time.sleep(self.request_delay)

        return articles

    def get_pdf_url(self, article_url: str) -> Optional[str]:
        """Acessa a página do artigo e tenta encontrar o PDF"""

        response = requests.get(
            article_url,
            headers=self.headers,
            timeout=15
        )

        if response.status_code != 200:
            logger.warning(f"Erro ao acessar artigo: {article_url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        pdf_link = soup.find("a", attrs={"data-track-action": "download pdf"})
        if not pdf_link:
            logger.warning(f"PDF não encontrado: {article_url}")
            return None

        return "https://www.nature.com" + pdf_link["href"]


    def download_pdf(self, pdf_url: str, filename: str) -> bool:
        """Baixa o PDF e salva localmente"""

        pdf_path = self.pdf_dir / filename

        if pdf_path.exists():
            logger.info(f"PDF já existe: {filename}")
            return True

        response = requests.get(
            pdf_url,
            headers=self.headers,
            stream=True,
            timeout=20
        )

        if response.status_code != 200:
            logger.warning(f"Erro ao baixar PDF: {pdf_url}")
            return False
        
        with open(pdf_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"PDF salvo: {filename}")
        time.sleep(self.request_delay)
        return True


    def run(self) -> List[Path]:
        """
        Executa o scraper completo
        busca artigos → baixa PDFs
        """
        downloaded_pdfs = []

        articles = self.search_articles()

        for article in articles:
            pdf_url = self.get_pdf_url(article["article_url"])
            if not pdf_url:
                continue

            safe_title = article["title"].replace(" ", "_").replace("/", "")
            filename = f"{safe_title}.pdf"

            success = self.download_pdf(pdf_url, filename)
            if success:
                downloaded_pdfs.append(self.pdf_dir / filename)

        logger.info(f"Total de PDFs baixados: {len(downloaded_pdfs)}")
        return downloaded_pdfs
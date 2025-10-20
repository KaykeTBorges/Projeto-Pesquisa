from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from oer_scraper.utils import (
    LOGGER,
    get_soup,
    wait_request_delay,
    save_metadata_dataframe,
    download_html_if_allowed,
    safe_filename_from_doi
)
from oer_scraper import config


def scrape_articles_metadata_and_html(max_pages: int = config.MAX_PAGES):
    """
    Scraper principal:
    1. Coleta metadados da página de busca da Nature.
    2. Baixa HTML completo de artigos gratuitos.
    3. Salva CSV com metadados + caminho do HTML.
    """

    # Carregar CSV existente (checkpoint)
    metadata_path = Path(config.METADATA_CSV)
    if metadata_path.exists():
        df_metadata = pd.read_csv(metadata_path)
        LOGGER.info("CSV existente carregado: %d artigos", len(df_metadata))
    else:
        df_metadata = pd.DataFrame()

    all_articles = []

    # Iterar páginas de busca
    for page in range(1, max_pages + 1):
        url = f"{config.BASE_URL}?q={config.SEARCH_QUERY}&date_range={config.YEAR_RANGE}&page={page}"
        LOGGER.info("Acessando página %d: %s", page, url)

        soup = get_soup(url)
        if not soup:
            LOGGER.warning("Falha ao obter soup da página %d", page)
            continue

        # Seletores CSS para cada artigo (ajustar conforme HTML real)
        article_cards = soup.select("div.app-article-list-row")  # placeholder
        LOGGER.info("Artigos encontrados nesta página: %d", len(article_cards))

        for card in article_cards:
            # --- Extrair metadados ---
            try:
                title_tag = card.select_one("h2 a")
                title = title_tag.get_text(strip=True)
                link = "https://www.nature.com" + title_tag["href"]
            except Exception:
                LOGGER.warning("Erro ao extrair título/link")
                continue

            doi_tag = card.select_one("span[data-track-action='doi']")
            doi = doi_tag.get_text(strip=True) if doi_tag else title.replace(" ", "_")

            authors_tag = card.select_one("ul.c-author-list")
            authors = authors_tag.get_text(separator=", ") if authors_tag else ""

            journal_tag = card.select_one("span.c-meta__type")
            journal = journal_tag.get_text(strip=True) if journal_tag else "Nature"

            year_tag = card.select_one("time")
            year = year_tag.get_text(strip=True) if year_tag else "Unknown"

            abstract_tag = card.select_one("div.c-card__summary")
            abstract = abstract_tag.get_text(strip=True) if abstract_tag else ""

            # --- Checar se já foi processado pelo checkpoint ---
            if not df_metadata.empty:
                if ((df_metadata["doi"] == doi).any()):
                    LOGGER.debug("Artigo já processado (checkpoint): %s", doi)
                    continue

            # --- Baixar HTML completo ---
            html_path = download_html_if_allowed(url=link, year=year, journal=journal, doi=doi)
            if html_path is None:
                LOGGER.info("HTML não salvo (paywall ou erro): %s", link)
                continue  # pular artigo paywalled

            # --- Adicionar artigo à lista ---
            article_info = {
                "title": title,
                "link": link,
                "doi": doi,
                "authors": authors,
                "year": year,
                "journal": journal,
                "abstract": abstract,
                "html_path": str(html_path),  # path do HTML
                "paywalled": False,          # sempre False, porque não salvamos pagos
                "processed": True            # checkpoint
            }

            all_articles.append(article_info)

            # Delay entre requisições para evitar bloqueio
            wait_request_delay()

        LOGGER.info("Página %d processada", page)

    # --- Salvar CSV final (checkpoint) ---
    if all_articles:
        df_new = pd.DataFrame(all_articles)
        if not df_metadata.empty:
            df_final = pd.concat([df_metadata, df_new], ignore_index=True)
        else:
            df_final = df_new

        save_metadata_dataframe(df_final)
        LOGGER.info("Scraping finalizado: total de artigos processados: %d", len(df_final))
    else:
        LOGGER.info("Nenhum artigo novo processado.")


if __name__ == "__main__":
    scrape_articles_metadata_and_html()
import pandas as pd
import re
import spacy
from bs4 import BeautifulSoup
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Importar configuração do mesmo pacote
from . import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.BASE_DIR / 'parser.log'),
        logging.StreamHandler()
    ]
)

class NatureHTMLParser:
    """Parser para extrair informações técnicas de HTMLs de artigos da Nature"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logging.info("Modelo spaCy carregado com sucesso")
        except OSError:
            logging.error("Modelo spaCy 'en_core_web_sm' não encontrado.")
            logging.info("Execute: python -m spacy download en_core_web_sm")
            raise
        
        self.overpotential_patterns = [
            r'overpotential[\s\S]{0,200}?(\d+\.?\d*)\s*[mM]?[Vv]',
            r'η[\s\S]{0,200}?(\d+\.?\d*)\s*[mM]?[Vv]',
            r'(\d+\.?\d*)\s*[mM]?[Vv][\s\S]{0,200}?overpotential',
            r'overpotential\s*of\s*(\d+\.?\d*)\s*[mM]?[Vv]',
            r'η\s*=\s*(\d+\.?\d*)\s*[mM]?[Vv]'
        ]
        
    def load_html(self, html_path: str) -> Optional[str]:
        try:
            path_obj = Path(html_path)
            if not path_obj.exists():
                logging.warning(f"Arquivo HTML não encontrado: {html_path}")
                return None
            
            with open(path_obj, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logging.error(f"Erro ao carregar HTML {html_path}: {str(e)}")
            return None
    
    def extract_main_text(self, html_content: str) -> str:
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            article_body = soup.find('div', class_='c-article-body')
            if article_body:
                paragraphs = article_body.find_all('p')
                text_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                return ' '.join(text_parts)
            
            main_content = soup.find('main') or soup.find('article')
            if main_content:
                paragraphs = main_content.find_all('p')
                text_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
                return ' '.join(text_parts)
            
            paragraphs = soup.find_all('p')
            text_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    text_parts.append(text)
            
            main_text = ' '.join(text_parts)
            
            if len(main_text) < 200:
                logging.warning("Texto extraído muito curto")
            
            return main_text
            
        except Exception as e:
            logging.error(f"Erro ao extrair texto do HTML: {str(e)}")
            return ""
    
    def extract_overpotential(self, text: str) -> Optional[float]:
        if not text:
            return None
            
        text_lower = text.lower()
        
        for pattern in self.overpotential_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match)
                    context = re.search(pattern.replace(r'(\d+\.?\d*)', match), text_lower)
                    if context:
                        context_text = context.group(0)
                        if ' v' in context_text and value < 10:
                            value = value * 1000
                    
                    if 10 <= value <= 1000:
                        logging.info(f"Overpotential encontrado: {value} mV")
                        return round(value, 2)
                except ValueError:
                    continue
        
        return None
    
    def extract_key_terms(self, text: str) -> Dict[str, bool]:
        if not text:
            return {term: False for term in config.KEY_TERMS}
            
        text_lower = text.lower()
        term_presence = {}
        
        for term in config.KEY_TERMS:
            term_lower = term.lower()
            pattern = r'\b' + re.escape(term_lower) + r'\b'
            term_presence[term] = bool(re.search(pattern, text_lower, re.IGNORECASE))
        
        return term_presence
    
    def parse_single_article(self, row: pd.Series) -> Dict:
        article_data = row.to_dict()
        
        html_path = row.get('html_path', '')
        if not html_path:
            logging.warning(f"Campo html_path vazio para: {row.get('title', 'Unknown')}")
            return article_data
        
        if not os.path.exists(html_path):
            logging.warning(f"HTML não encontrado: {html_path}")
            return article_data
        
        html_content = self.load_html(html_path)
        if not html_content:
            return article_data
        
        main_text = self.extract_main_text(html_content)
        article_data['text_length'] = len(main_text)
        
        if len(main_text) < 100:
            logging.warning(f"Texto muito curto ({len(main_text)} chars) para: {row.get('title', 'Unknown')}")
            return article_data
        
        overpotential = self.extract_overpotential(main_text)
        article_data['overpotential_mv'] = overpotential
        
        key_terms = self.extract_key_terms(main_text)
        article_data.update(key_terms)
        
        logging.info(f"Artigo processado: {row.get('title', 'Unknown')} "
                    f"(Overpotential: {overpotential}, Texto: {len(main_text)} chars)")
        
        return article_data
    
    def process_all_articles(self) -> pd.DataFrame:
        try:
            if not os.path.exists(config.METADATA_CSV):
                logging.error(f"Arquivo de metadados não encontrado: {config.METADATA_CSV}")
                return pd.DataFrame()
            
            metadata_df = pd.read_csv(config.METADATA_CSV)
            logging.info(f"Carregados {len(metadata_df)} artigos para processamento")
            
            if metadata_df.empty:
                logging.warning("Nenhum artigo encontrado no CSV de metadados")
                return pd.DataFrame()
            
            articles_with_html = metadata_df[metadata_df['html_path'].notna() & (metadata_df['html_path'] != '')]
            logging.info(f"{len(articles_with_html)} artigos com caminhos de HTML válidos")
            
            if articles_with_html.empty:
                logging.warning("Nenhum artigo com HTML válido encontrado")
                return pd.DataFrame()
            
            processed_data = []
            for idx, row in articles_with_html.iterrows():
                try:
                    article_result = self.parse_single_article(row)
                    processed_data.append(article_result)
                    
                    if (idx + 1) % 5 == 0:
                        logging.info(f"Processados {idx + 1}/{len(articles_with_html)} artigos")
                        
                except Exception as e:
                    logging.error(f"Erro ao processar artigo {idx}: {str(e)}")
                    processed_data.append(row.to_dict())
            
            result_df = pd.DataFrame(processed_data)
            
            os.makedirs(os.path.dirname(config.PROCESSED_DIR), exist_ok=True)
            output_path = config.PROCESSED_DIR / "articles_parsed.csv"
            result_df.to_csv(output_path, index=False, encoding='utf-8')
            
            logging.info(f"Processamento concluído. Resultados salvos em: {output_path}")
            logging.info(f"Artigos processados com sucesso: {len(result_df)}")
            
            if not result_df.empty:
                overpotential_count = result_df['overpotential_mv'].notna().sum()
                logging.info(f"Artigos com overpotential extraído: {overpotential_count}")
                
                for term in config.KEY_TERMS[:10]:
                    if term in result_df.columns:
                        term_count = result_df[term].sum()
                        logging.info(f"Artigos com '{term}': {term_count}")
            
            return result_df
            
        except Exception as e:
            logging.error(f"Erro no processamento geral: {str(e)}")
            return pd.DataFrame()

def main():
    """Função principal para executar parsing standalone"""
    logging.info("Iniciando parser de artigos da Nature")
    
    try:
        parser = NatureHTMLParser()
        result_df = parser.process_all_articles()
        
        if not result_df.empty:
            logging.info("Pipeline de parsing concluída com sucesso!")
            logging.info(f"Total de artigos processados: {len(result_df)}")
        else:
            logging.warning("Nenhum dado foi processado")
            
    except Exception as e:
        logging.error(f"Erro na execução do parser: {str(e)}")
        raise

if __name__ == "__main__":
    main()
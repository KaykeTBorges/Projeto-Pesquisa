import pandas as pd
import re
import spacy
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from . import config
from .logger import get_parser_logger

# Configurar logger
logger = get_parser_logger()

class MLReadyParser:
    """Parser otimizado para dados de Machine Learning"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Modelo spaCy carregado com sucesso")
        except OSError:
            logger.warning("spaCy não disponível - usando regex apenas")
            self.nlp = None
        
        # Padrões regex para extração quantitativa
        self.patterns = {
            'overpotential': [
                r'overpotential[\s\S]{0,200}?(\d+\.?\d*)\s*[mM]?[Vv]',
                r'η[\s\S]{0,200}?(\d+\.?\d*)\s*[mM]?[Vv]',
                r'η\s*=\s*(\d+\.?\d*)\s*[mM]?[Vv]'
            ],
            'current_density': [
                r'(\d+\.?\d*)\s*mA\s*cm[⁻¹\-]?2',
                r'current density[\s\S]{0,100}?(\d+\.?\d*)\s*mA',
                r'j\s*=\s*(\d+\.?\d*)\s*mA'
            ],
            'ph': [
                r'pH\s*[=:\s]*(\d+\.?\d*)',
                r'at pH\s*(\d+\.?\d*)'
            ],
            'temperature': [
                r'(\d+\.?\d*)\s*°?C',
                r'temperature[\s\S]{0,50}?(\d+\.?\d*)\s*°?C'
            ],
            'tafel_slope': [
                r'Tafel slope[\s\S]{0,100}?(\d+\.?\d*)\s*mV',
                r'(\d+\.?\d*)\s*mV\s*dec[⁻¹\-]?1',
                r'slope[\s\S]{0,50}?(\d+\.?\d*)\s*mV'
            ],
            'stability': [
                r'stability[\s\S]{0,100}?(\d+\.?\d*)\s*h',
                r'stable[\s\S]{0,100}?(\d+\.?\d*)\s*h',
                r'(\d+\.?\d*)\s*hour'
            ]
        }

    def extract_main_text(self, soup: BeautifulSoup) -> str:
        """Extrair texto principal do HTML"""
        # Tentar diferentes seletores
        selectors = [
            'div.c-article-body',
            'article',
            'main',
            '.article-content',
            '.c-article-main-content'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if len(text) > 500:  # Texto suficientemente longo
                    return text
        
        # Fallback: todos os parágrafos
        paragraphs = soup.find_all('p')
        text_parts = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 50:  # Filtrar parágrafos muito curtos
                text_parts.append(text)
        
        main_text = ' '.join(text_parts)
        
        if len(main_text) < 200:
            logger.warning(f"Texto extraído muito curto: {len(main_text)} caracteres")
        
        return main_text

    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extrair metadados básicos"""
        metadata = {}
        
        # Título
        title_elem = soup.find('h1', class_='c-article-title') or soup.find('title')
        if title_elem:
            metadata['title'] = title_elem.get_text(strip=True)
        
        # Autores
        authors = []
        author_elems = soup.select('[data-test="author-name"], .c-article-author-list a, .c-author-list a')
        for elem in author_elems:
            author = elem.get_text(strip=True)
            if author and len(author) > 2:
                authors.append(author)
        metadata['authors'] = '; '.join(authors)
        
        # Data
        date_elem = soup.find('time') or soup.select_one('[datetime]')
        if date_elem:
            date_text = date_elem.get('datetime') or date_elem.get_text()
            year_match = re.search(r'20\d{2}', date_text)
            if year_match:
                metadata['year'] = int(year_match.group())
        
        # Open Access
        oa_indicators = soup.select('.c-article-access, [data-test="open-access"], .open-access')
        metadata['open_access'] = len(oa_indicators) > 0
        
        # DOI
        doi_elem = soup.find('meta', attrs={'name': 'citation_doi'})
        if doi_elem:
            metadata['doi'] = doi_elem.get('content', '')
        else:
            metadata['doi'] = self.extract_doi_from_url(url)
        
        return metadata

    def extract_doi_from_url(self, url: str) -> str:
        """Extrair DOI da URL"""
        match = re.search(r'articles/([^/?]+)', url)
        return match.group(1) if match else ''
    
    def extract_numeric_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extrair valor numérico usando múltiplos padrões"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match)
                    return value
                except ValueError:
                    continue
        return None
    
    def extract_quantitative_features(self, text: str) -> Dict[str, Optional[float]]:
        """Extrair features quantitativas para ML"""
        features = {}
        
        for feature_name, patterns in self.patterns.items():
            value = self.extract_numeric_value(text, patterns)
            features[feature_name] = value
        
        return features
    
    def extract_element_counts(self, text: str) -> Dict[str, int]:
        """Contar ocorrências de elementos (para features de composição)"""
        counts = {}
        
        for element in config.ELEMENTS:
            # Padrão para elemento como palavra completa
            pattern = r'\b' + re.escape(element) + r'\b'
            count = len(re.findall(pattern, text, re.IGNORECASE))
            counts[f'element_{element}'] = count
        
        return counts
    
    def extract_compound_presence(self, text: str) -> Dict[str, int]:
        """Verificar presença de compostos específicos"""
        presence = {}
        
        for compound in config.COMPOUNDS:
            pattern = r'\b' + re.escape(compound) + r'\b'
            presence[f'compound_{compound}'] = 1 if re.search(pattern, text, re.IGNORECASE) else 0
        
        return presence
    
    def extract_material_properties(self, text: str) -> Dict[str, int]:
        """Extrair propriedades de materiais"""
        properties = {}
        
        # Tipos de materiais
        for material in config.MATERIAL_TYPES:
            pattern = r'\b' + re.escape(material) + r'\b'
            properties[f'material_{material}'] = 1 if re.search(pattern, text, re.IGNORECASE) else 0
        
        # Morfologias
        for morphology in config.MORPHOLOGIES:
            pattern = r'\b' + re.escape(morphology) + r'\b'
            properties[f'morphology_{morphology}'] = 1 if re.search(pattern, text, re.IGNORECASE) else 0
        
        # Substratos
        for substrate in config.SUBSTRATES:
            pattern = r'\b' + re.escape(substrate) + r'\b'
            properties[f'substrate_{substrate}'] = 1 if re.search(pattern, text, re.IGNORECASE) else 0
        
        return properties
    
    def extract_experimental_conditions(self, text: str) -> Dict[str, any]:
        """Extrair condições experimentais"""
        conditions = {}
        
        # Eletrólitos
        electrolyte_found = None
        for electrolyte in config.ELECTROLYTES:
            if re.search(r'\b' + re.escape(electrolyte) + r'\b', text, re.IGNORECASE):
                electrolyte_found = electrolyte
                break
        conditions['electrolyte'] = electrolyte_found
        
        # Concentração de eletrólito
        concentration_match = re.search(r'(\d+\.?\d*)\s*M', text, re.IGNORECASE)
        conditions['electrolyte_concentration'] = float(concentration_match.group(1)) if concentration_match else None
        
        return conditions
    
    def extract_performance_metrics(self, text: str) -> Dict[str, any]:
        """Extrair métricas de performance"""
        metrics = {}
        
        for term in config.PERFORMANCE_TERMS:
            # Verificar menção
            pattern = r'\b' + re.escape(term) + r'\b'
            metrics[f'mentions_{term}'] = 1 if re.search(pattern, text, re.IGNORECASE) else 0
        
        # Eficiência Faradaica
        fe_match = re.search(r'faradaic efficiency[\s\S]{0,100}?(\d+\.?\d*)%', text, re.IGNORECASE)
        metrics['faradaic_efficiency'] = float(fe_match.group(1)) if fe_match else None
        
        # Frequência de turnover
        tof_match = re.search(r'turnover frequency[\s\S]{0,100}?(\d+\.?\d*)', text, re.IGNORECASE)
        metrics['turnover_frequency'] = float(tof_match.group(1)) if tof_match else None
        
        return metrics
    
    def extract_text_metrics(self, text: str) -> Dict[str, int]:
        """Métricas do texto para features de contexto"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        return {
            'text_length': len(text),
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if len(s.strip()) > 0]),
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'unique_words': len(set(words))
        }
    
    def parse_single_article(self, html_path: str, url: str) -> Dict:
        """Processar um único artigo e retornar dados ricos para ML"""
        try:
            # Carregar HTML
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extrair texto principal
            soup = BeautifulSoup(html_content, 'lxml')
            main_text = self.extract_main_text(soup)
            
            if len(main_text) < 200:
                logger.warning(f"Texto muito curto: {len(main_text)} caracteres")
                return None
            
            # Inicializar dados do artigo
            article_data = {
                'url': url,
                'doi': self.extract_doi_from_url(url),
                'html_path': str(html_path),
                'text_length': len(main_text)
            }
            
            # Extrair metadados básicos
            metadata = self.extract_metadata(soup, url)
            article_data.update(metadata)
            
            # EXTRAIR FEATURES PARA ML
            article_data.update(self.extract_quantitative_features(main_text))
            article_data.update(self.extract_element_counts(main_text))
            article_data.update(self.extract_compound_presence(main_text))
            article_data.update(self.extract_material_properties(main_text))
            article_data.update(self.extract_experimental_conditions(main_text))
            article_data.update(self.extract_performance_metrics(main_text))
            article_data.update(self.extract_text_metrics(main_text))
            
            logger.info(f"📊 Artigo processado: {article_data.get('title', 'Unknown')}")
            logger.info(f"   🔢 Features: {len([k for k in article_data.keys() if not k in ['url', 'title', 'authors']])}")
            
            return article_data
            
        except Exception as e:
            logger.error(f"Erro ao processar {html_path}: {e}")
            return None

def main():
    """Função principal para processamento em lote"""
    logger.info("Iniciando parser ML-ready")
    
    try:
        parser = MLReadyParser()
        
        # Processar todos os HTMLs existentes
        html_files = list(config.RAW_DIR.glob("*.html"))
        logger.info(f"Encontrados {len(html_files)} HTMLs para processar")
        
        all_data = []
        for html_file in html_files:
            # Tentar extrair URL do arquivo ou usar placeholder
            url = f"https://www.nature.com/articles/{html_file.stem}"
            article_data = parser.parse_single_article(html_file, url)
            if article_data:
                all_data.append(article_data)
        
        # Salvar resultados
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(config.METADATA_CSV, index=False)
            logger.info(f"✅ Processamento concluído: {len(df)} artigos salvos")
        else:
            logger.warning("Nenhum dado processado")
            
    except Exception as e:
        logger.error(f"Erro: {e}")
        raise

if __name__ == "__main__":
    main()
import pandas as pd
import re # regex, expressões regulares
import pdfplumber
from pathlib import Path # para manipulação de caminhos de arquivos, OO Python
from typing import List, Dict, Optional # para tipagem de dados
import sys # para manipulação de sistema operacional, mexer diretamente com o sistema operacional e execução

from oer_scraper import config # para importação de configurações
from oer_scraper.logger import get_parser_logger # para registro de logs

logger = get_parser_logger()

class Parser:
    """Parser para extrair dados do PDF de artigos de OER da Nature"""

    def __init__(self):
        # Usar configurações do config.py
        self.patterns = config.PATTERNS
        self.catalyst_keywords = config.CATALYST_KEYWORDS
        self.substrate_keywords = config.SUBSTRATE_KEYWORDS
        self.electrolyte_keywords = config.ELECTROLYTE_KEYWORDS

        self.catalyst_patterns = config.CATALYST_PATTERNS
        self.substrate_patterns = config.SUBSTRATE_PATTERNS
        self.min_text_length = config.MIN_TEXT_LENGTH

        self.overpotential_patterns = config.PATTERNS['overpotential']
        self.electrolyte_patterns = config.PATTERNS['electrolyte']

        logger.info("Parser configurado com listas do config.py")


    def _split_sentences(self, text: str) -> List[str]:
        """
        Divide o texto em sentenças de forma simples.
        Evita aplicar regex no texto inteiro do PDF.
        """
        text = re.sub(r'\s+', ' ', text)
        return re.split(r'(?<=[.;])\s+', text)


    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrai todo o texto de um PDF"""
        full_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text
            
            if len(full_text) < self.min_text_length:
                logger.warning(f"Texto muito curto em {pdf_path}, pulando...")

            return full_text
        except Exception as e:
            logger.error(f"Erro ao ler o PDF {pdf_path}: {e}")
            return None
        
    def find_catalyst(self, text: str) -> Optional[str]:
        """Identifica um eletrocatalisador no texto"""
        for pattern in self.catalyst_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE) # findall: encontra todas as ocorrências de um padrão em um texto, o findall funciona como o de prolog
            for match in matches:
                candidate = match.strip()
                # Verifica se contém nas palavras-chave de catalisador
                # pode demorar porque vai usar o regex e não tem já pré-definido fora do for
                # mas como é algo que temos tempo, não vou definir os regex fora do for
                for catalyst in self.catalyst_keywords:
                    if catalyst.lower() in candidate.lower():
                        return candidate
        
        for catalyst in self.catalyst_keywords:
            if re.search(r'\b' + re.escape(catalyst) + r'\b', text, re.IGNORECASE):
                return catalyst
        
        return None

    def find_substrate(self, text: str) -> Optional[str]:
        """Identifica o substrato utilizado no texto"""
        for pattern in self.substrate_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                candidate = match.strip()
                for substrate in self.substrate_keywords:
                    if substrate.lower() in candidate.lower():
                        return candidate
        
        for substrate in self.substrate_keywords:
            if re.search(r'\b' + re.escape(substrate) + r'\b', text, re.IGNORECASE):
                return substrate
        
        return None
    
    # eu uso re findall nos acima, porque são entidades semânticas e precisam validar os candidatos
    # já o eletrólito e o sobrepotencial são valores

    def find_electrolyte(self, text: str) -> Optional[Dict[str, object]]:
        """
        Encontra o eletrólito/solução.
        Retorna um dicionário
        """
        sentences = self._split_sentences(text)

        candidates = []

        for sent in sentences:
            sent_lower = sent.lower()

            # Camada 1 — contexto científico
            if any(k in sent_lower for k in ["catalyst", "electrocatalyst"]):

                # Camada 2 — capturar frase candidata
                match = re.search(
                    r'([A-Z][A-Za-z0-9\-\(\)/·–\s]{5,80})\s*(?:catalyst|electrocatalyst)',
                    sent
                )

                if match:
                    name = match.group(1).strip()

                    # Filtro simples de qualidade
                    if len(name.split()) >= 2:
                        candidates.append(name)

        return candidates[0] if candidates else None
    
    def find_overpotential(self, text: str) -> Optional[Dict[str, any]]:
        """
        Encontra apenas o sobrepotencial e sua grandeza.
        Retorna um dicionário
        """
        sentences = self._split_sentences(text)

        candidates = []

        for sent in sentences:
            sent_lower = sent.lower()

        # Camada 1 — filtro contextual
            if any(k in sent_lower for k in ["overpotential", "η", "mv", " v"]):

                # Camada 2 — regex simples e robusto
                matches = re.finditer(
                    r'(η|overpotential)?\s*=?\s*(\d{2,4})\s*(mV|mv|V|v)',
                    sent,
                    re.IGNORECASE
                )

                for match in matches:
                    try:
                        value = float(match.group(2))
                        unit = match.group(3).lower()

                        # Padronizar unidade
                        if unit == 'v':
                            value *= 1000

                        # Validação física básica
                        if 10 <= value <= 2000:
                            candidates.append(value)

                    except (ValueError, IndexError):
                        continue

        if not candidates:
            return None

        # Heurística: menor sobrepotencial reportado
        best_value = min(candidates)

        return {
            'value': round(best_value, 2),
            'unit': 'mV'
        }

    def parse_pdf(self, pdf_path: str) -> Optional[Dict[str, object]]:
        """Faz o parsing completo de um PDF e retorna apenas as 4 informações principais"""

        logger.info(f"Iniciando parsing do PDF: {pdf_path}")

        text = self.extract_text_from_pdf(pdf_path)

        if not text:
            logger.warning(f"Texto inválido ou vazio em {pdf_path}")
            return None

        catalyst = self.find_catalyst(text)
        substrate = self.find_substrate(text)
        electrolyte = self.find_electrolyte(text)
        overpotential = self.find_overpotential(text)

        parsed_data = {
            "pdf_name": Path(pdf_path).name,
            "catalyst": catalyst,
            "substrate": substrate,
            "electrolyte": electrolyte,
            "overpotential": overpotential
        }

        logger.info(
            f"Parsing concluído | "
            f"Catalyst={bool(catalyst)} | "
            f"Substrate={bool(substrate)} | "
            f"Electrolyte={bool(electrolyte)} | "
            f"Overpotential={bool(overpotential)}"
        )

        return parsed_data

    def main():
        """Processa todos os PDFs da pasta RAW"""

        parser = Parser()
        results = []

        for pdf_file in config.PDF_DIR.glob("*.pdf"):
            parsed = parser.parse_pdf(pdf_file)
            if parsed:
                results.append(parsed)

        if results:
            df = pd.DataFrame(results)
            df.to_csv(config.PARSED_DATA_CSV, index=False)

            logger.info(f"{len(df)} PDFs processados com sucesso.")
        else:
            logger.warning("Nenhum PDF válido processado.")

    if __name__ == "__main__":
        main()
      

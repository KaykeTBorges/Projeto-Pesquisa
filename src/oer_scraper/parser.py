import pdfplumber
import re
import json
from pathlib import Path
from typing import List, Dict, Optional

from google import genai
from google.genai import types

from oer_scraper import config
from oer_scraper.logger import get_parser_logger

logger = get_parser_logger()


class Parser:
    """Parser que extrai texto do PDF e usa IA para extrair dados de OER"""

    def __init__(self):

        self.min_text_length = config.MIN_TEXT_LENGTH
        self.keywords = config.KEYWORDS_FILTER

        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

        logger.info("Parser inicializado com modelo de IA")


    # -------------------------------------------------
    # EXTRAÇÃO DE TEXTO
    # -------------------------------------------------

    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extrai texto completo de um PDF"""

        full_text = ""

        try:

            with pdfplumber.open(pdf_path) as pdf:

                for page in pdf.pages:

                    # layout=True mantém o posicionamento visual do texto tentando respeitar
                    # colunas esquerdas e direitas, separando com espaços.
                    text = page.extract_text(layout=True)

                    if text:
                        full_text += text + "\n"

            if len(full_text) < self.min_text_length:

                logger.warning(f"Texto muito curto em {pdf_path}")
                return None

            return full_text

        except Exception as e:

            logger.error(f"Erro ao ler PDF {pdf_path}: {e}")
            return None


    # -------------------------------------------------
    # EXTRAÇÃO POR JANELAS (SLIDING WINDOW)
    # -------------------------------------------------

    def extract_windows(self, text: str) -> List[str]:
        """Extrai janelas de texto ao redor de palavras-chave (config.WINDOW_SIZE)"""
        text_lower = text.lower()
        matches = []
        
        for kw in self.keywords:
            for match in re.finditer(re.escape(kw), text_lower):
                matches.append(match.start())
                
        matches.sort()
        
        if not matches:
            return []
            
        merged_windows = []
        current_start = None
        current_end = None
        
        half_window = config.WINDOW_SIZE // 2
        
        for idx in matches:
            start_pos = max(0, idx - half_window)
            end_pos = min(len(text), idx + half_window)
            
            if current_start is None:
                current_start = start_pos
                current_end = end_pos
            else:
                # Se sobrepõe ou fica muito perto, unifica as janelas
                if start_pos <= current_end + 100:
                    current_end = max(current_end, end_pos)
                else:
                    merged_windows.append(text[current_start:current_end])
                    current_start = start_pos
                    current_end = end_pos
                    
        if current_start is not None:
            merged_windows.append(text[current_start:current_end])
            
        return merged_windows


    # -------------------------------------------------
    # EXTRAÇÃO COM IA
    # -------------------------------------------------

    def extract_with_ai(self, text: str) -> Optional[Dict]:

        prompt = f"""
        Extract the SINGLE MAIN OER catalyst information from the following text snippets (which may contain multiple distinct catalysts, but you must identify the primary one being studied or offering the best results).

        Return a SINGLE JSON object with the fields:

        material
        substrate
        current_density
        overpotential_mV

        Rules:

        - current_density should be numeric (mA/cm²)
        - overpotential must be in mV
        - if potential is in V vs RHE convert:
          (V - 1.23) * 1000
        - if a value is missing return null
        - Analyze all snippets and return ONLY ONE JSON object representing the absolute best/primary catalyst. Do NOT return a list or array.

        Text snippets:
        {text}
        """
        try:

            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            json_text = response.text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            data = json.loads(json_text)
            
            # Se o Gemini desobedecer e retornar uma lista, pegamos o primeiro item
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    return None
                    
            # Se ele retornou um dicionário vazio ou só com nulos
            if not data or not any(data.values()):
                return None

            return data

        except Exception as e:

            logger.warning(f"Erro na extração com IA: {e}")
            return None


    # -------------------------------------------------
    # PARSE COMPLETO
    # -------------------------------------------------

    def parse_pdf(self, pdf_path: Path) -> List[Dict]:

        logger.info(f"Processando {pdf_path.name}")

        text = self.extract_text_from_pdf(pdf_path)

        if not text:
            return []

        windows = self.extract_windows(text)

        logger.info(f"{len(windows)} janelas relevantes encontradas")
        
        if not windows:
            return []

        # IMPLEMENTAÇÃO DO BATCHING (Agrupamento de Requisições)
        # Juntamos todas as janelas usando uma tag separadora.
        # Assim faremos apenas UMA ÚNICA chamada à API por documento inteiro, gastando 1 requisição.
        combined_text = "\n\n--- PRÓXIMO TRECHO ---\n\n".join(windows)

        data = self.extract_with_ai(combined_text)

        results = []

        if data and isinstance(data, dict):
            data["source_pdf"] = pdf_path.name
            results.append(data)

        return results
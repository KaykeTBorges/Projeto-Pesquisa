#!/usr/bin/env python3
"""
Script principal para executar a pipeline OER
Execute este script a partir do diretório raiz do projeto
"""

import sys
from pathlib import Path

# Adicionar o diretório src ao path para importar o pacote oer_scraper
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

from oer_scraper.pipeline_oer import main

if __name__ == "__main__":
    main()
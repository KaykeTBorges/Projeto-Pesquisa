#!/usr/bin/env python3
"""
Script principal para executar a pipeline OER
Execute este script a partir do diretório raiz do projeto
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório src ao path para importar o pacote oer_scraper
project_root = Path(__file__).resolve().parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Mudar para o diretório do projeto
os.chdir(project_root)

def main():
    """Função principal"""
    try:
        from oer_scraper.pipeline_ml_ready import main as pipeline_main
        pipeline_main()
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("📁 Verificando estrutura de arquivos...")
        
        # Listar arquivos para debug
        oer_scraper_dir = src_dir / "oer_scraper"
        if oer_scraper_dir.exists():
            print("📂 Arquivos em oer_scraper/:")
            py_files = list(oer_scraper_dir.glob("*.py"))
            if py_files:
                for file in py_files:
                    print(f"   - {file.name}")
            else:
                print("   ❌ Nenhum arquivo .py encontrado")
        else:
            print(f"❌ Diretório não encontrado: {oer_scraper_dir}")
        
        print("\n🔧 Solução de problemas:")
        print("   1. Verifique se a pasta 'src/oer_scraper' existe")
        print("   2. Verifique se todos os arquivos .py estão presentes")
        print("   3. Execute: python -m src.oer_scraper.pipeline_ml_ready")
        
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Execução interrompida pelo usuário")
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
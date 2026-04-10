# Relatório Parcial de Pesquisa

Este documento serve como base explicativa para o preenchimento do **Relatório Parcial de Pesquisa** (SIGAA), estruturando tudo o que foi realizado no projeto de raspagem e análise de dados de catalisadores para a Reação de Evolução de Oxigênio (OER).

## 1. Atividades Realizadas
Até o momento, o núcleo central da pesquisa (o pipeline automatizado de extração) foi construído e validado. As principais atividades concluídas incluem:

*   **Desenvolvimento do Scraper Automatizado:** Criação de um módulo em Python ([scraper.py](file:///home/ktb/workspace/github.com/KaykeTBorges/Projeto-Pesquisa/src/oer_scraper/scraper.py)) para buscar e baixar automaticamente artigos científicos (PDFs) no portal da Nature, focando em "oxygen evolution reaction" ou "OER".
*   **Implementação de Tolerância a Falhas:** Configuração de sessões com o módulo `urllib3` e `requests` para utilizar estratégias de *Retry* automático (lidando com erros 429, 500, etc.) e delays configuráveis, evitando bloqueios por taxa de requisição.
*   **Conversão e Processamento de PDFs:** Uso da biblioteca `pdfplumber` com preservação visual (layout) para extrair o texto completo dos artigos de forma estruturada.
*   **Estratégia de Extração por Janelas Deslizantes (*Sliding Window*):** Desenvolvimento de um algoritmo que mapeia palavras-chave (ex: "overpotential", "mA/cm", "rhe") e recorta apenas as janelas de texto relevantes ao redor delas, eliminando ruído e textos inúteis do PDF.
*   **Integração com Inteligência Artificial (Gemini):** Implementação de chamadas otimizadas à API do modelo Gemini 2.5 Flash, passando as janelas relevantes de texto para a IA extrair os dados químicos brutos diretamente em formato JSON (Material, Substrato, Densidade de Corrente e Sobrepotencial).
*   **Criação do Pipeline End-to-End:** Estruturação do [pipeline.py](file:///home/ktb/workspace/github.com/KaykeTBorges/Projeto-Pesquisa/src/pipeline.py) que integra todo o fluxo (Busca -> Download -> Janela de Texto -> IA -> Salvamento em CSV) operando de maneira incremental.

## 2. Comparação entre Plano Original e Executado
*   **Plano Original / Tentativas Iniciais:** Nos commits iniciais, o projeto tentava realizar o download do HTML bruto das páginas e extrair vastas quantidades de dados via expressões regulares (Regex) ou manipulações complexas de HTML via `BeautifulSoup` (`parse_html.py`).
*   **Executado / Atualização de Rota:** Foi identificado que a raspagem de HTML era extremamente frágil devido aos diferentes layouts de revistas e *paywalls*. O escopo foi redirecionado para:
    1.  **Foco exclusivo nos 4 objetivos principais:** Focar apenas na extração cirúrgica de *Material*, *Substrato*, *Densidade de Corrente* e *Sobrepotencial*, ignorando dados periféricos.
    2.  **Substituição de Regex por IA:** A abstração da extração complexa passou do código estático (expressões regulares que falhavam constantemente) para um *prompt* robusto na API do Gemini.
    3.  **Filtragem pré-IA (Otimização de Custos/Limites):** Para não sobrecarregar a cota da IA, o texto lido no PDF é filtrado pelas "Janelas Deslizantes", e todas as janelas de um artigo são unidas e enviadas em apenas *um único lote (batch)* para o Gemini, tornando o processo altamente eficiente.

## 3. Outras Atividades Desenvolvidas
*   **Modernização da Estrutura do Projeto:** O gerenciamento de dependências foi migrado para padrões modernos utilizando arquivos [pyproject.toml](file:///home/ktb/workspace/github.com/KaykeTBorges/Projeto-Pesquisa/pyproject.toml) (com a ferramenta `uv`), isolando o ambiente virtual adequadamente.
*   **Segurança e Boas Práticas:** Implementação de arquivos `.dotenv` para separação de credenciais (API Keys do Gemini) e criação de regras de [.gitignore](file:///home/ktb/workspace/github.com/KaykeTBorges/Projeto-Pesquisa/.gitignore) para não expor PDFs, logs e chaves no repositório.
*   **Sistema de Log Centralizado:** Criação de um módulo [logger.py](file:///home/ktb/workspace/github.com/KaykeTBorges/Projeto-Pesquisa/src/oer_scraper/logger.py) que gera históricos isolados (`scraper.log`, `parser.log`, `pipeline.log`), facilitando muito a auditoria de erros e o acompanhamento do *pipeline* rodando em segundo plano.

## 4. Resultados Preliminares
O pipeline atual já encontra-se funcional e conseguiu gerar a primeira base de dados sólida `catalyst_data.csv`. Os dados preliminares processados pelo robô e extraídos pela IA incluem com sucesso os 4 parâmetros almejados. 

Exemplos de extrações que o sistema já conseguiu realizar autonomamente de diferentes PDFs:
*   **CoFe2O4** em *glassy carbon* gerando correntes de **1.6 mA/cm²** com sobrepotencial de **430 mV**.
*   **CoCr2O4** em *glassy carbon* a **10 mA/cm²** com sobrepotencial de **370 mV**.
*   **SI6C1** em *GCE* operando a **10 mA/cm²** e **245 mV**.
*   **Ruthenium-cobalt-tinoxide (A-RSCOH)** em *GCE*, atingindo a métrica de **10 mA/cm²** em apenas **193 mV**.

Estes dados comprovam **prova_de_conceito_aceita** para o fluxo programado. O script consegue não só identificar os elementos dopados e óxidos complexos, mas também isolar as métricas de performance (mV e mA/cm²) com sucesso e estruturá-las em formato tabular analítico (CSV), pronto para estudos comparativos ou aplicação de Machine Learning no futuro.

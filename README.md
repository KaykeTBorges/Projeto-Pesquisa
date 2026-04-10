# Research Project: OER Data Scraping and Analysis Pipeline

This repository contains the source code for an autonomous pipeline designed to scrape and extract data about catalysts for the Oxygen Evolution Reaction (OER).

The main idea of the system is to scan scientific publications (on the *Nature* portal), automatically download the articles (PDFs), and extract crucial parameters using intelligent text processing and AI.

## 📌 Main Extraction Goals
The pipeline is focused on accurately extracting the following electrochemical performance parameters:
- **Material** (e.g., complex oxides, doped materials, etc.)
- **Substrate** (e.g., *glassy carbon*)
- **Current Density** (in mA/cm²)
- **Overpotential** (in mV)

## ⚙️ Architecture and Pipeline
The end-to-end bot flow in `pipeline.py` follows these steps:
1. **Automated Search and Download (`scraper.py`)**: Performs intelligently ratelimited requests, detecting articles based on the DOI, and skipping previously processed documents.
2. **Sliding Window Filtering**: Instead of trying to parse HTML (which is fragile due to paywalls and varied layouts), we parse the PDF text via `pdfplumber` and apply "sliding windows". This crops out only the text surrounding key terms like "overpotential" and "mA/cm²".
3. **LLM Parser / Gemini (`parser.py`)**: The clean "windows" from each article are processed in batches by Google Gemini (2.5 Flash), which robustly extracts the chemical metrics into a structured JSON format with high certainty and low token cost.
4. **Dataset Generation (`catalyst_data.csv`)**: The validated output incrementally feeds a CSV database.

## 🛠️ Technologies and Libraries
* **Language**: Python 3.
* **Dependency Manager**: Modern standards using `uv` & `pyproject.toml`.
* **AI and Integration**: `google-genai` (Gemini API).
* **Data Parsing**: `pdfplumber` (PDF reading), `pandas` (Table compilation).
* **Network Requests**: `requests` adapted with robust retry logic using `urllib3`.

## 🚀 How to Run Locally

### 1. Clone and Setup Environment
Download the project and use `uv` (recommended) to install the dependencies.
```bash
git clone https://github.com/KaykeTBorges/Projeto-Pesquisa.git
cd Projeto-Pesquisa
uv sync
```

### 2. Environment Variables
The project depends on LLM credentials. Create a `.env` file at the root with your API key (do not commit this file):
```ini
GEMINI_API_KEY="your_google_ai_key_here"
```

### 3. Running the Pipeline
Simply run the main pipeline. The module will fetch new PDFs, download them to `/data/raw/pdf`, extract the results, and log executions to the `logs/` folder:
```bash
python src/pipeline.py
```

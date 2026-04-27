## Research Paper Decomposer
A personal CLI tool that uses Claude API to decompose academic research papers into structured operational blueprints: methodology, assumptions, data inputs, experimental design, evaluation metrics, and limitations.

## Features
- Section-aware document chunking — detects paper structure (Abstract, Methodology, Results, etc.) and sends relevant sections to Claude
- Schema-enforced prompt engineering — Claude returns validated JSON for each section
- JSON output validation — ensures all required fields are present before saving
- Clean formatted output saved as .txt next to your PDF

## Usage
python3 research.py "paper.pdf"

## Built With
- Claude API (multi-stage API calls)
- PyPDF2
- Python

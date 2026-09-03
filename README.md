# Groww Review Agent

An autonomous pipeline that ingests Play Store reviews for Groww, clusters them into actionable themes, and automatically delivers a Weekly Pulse via Google Docs and Gmail using LangChain and MCP servers.

## Setup

1. Copy `.env.example` to `.env` and configure your `GOOGLE_API_KEY`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run tests:
   ```bash
   pytest tests/
   ```

## Usage

Run the full pipeline:
```bash
python -m src.main
```

Or run individual steps:
```bash
python -m src.main --step ingest
python -m src.main --step analyze
python -m src.main --step deliver
python -m src.main --dry-run
```

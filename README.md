# SEC Filings Pipeline

Download the latest SEC 10-K filing for active public-company tickers and convert downloaded filing documents to Markdown.
Markdown conversion uses `sec2md` first so downloaded filings are transformed with SEC-aware structure instead of only generic HTML cleanup.

This project uses a modern Python `src/` layout:

```text
.
├── pyproject.toml
├── requirements.txt
├── README.md
├── src/
│   └── sec_filings/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── downloader.py
│       └── parser.py
└── tests/
    └── __init__.py
```

## Install

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development dependencies:

```bash
python -m pip install -e .[dev]
```

## Configuration

SEC requests should include contact information. Provide this through CLI flags or environment variables.

Environment variables:

- `SEC_PIPELINE_DATA_DIR` — base directory for downloaded filings, default: `/sec`
- `SEC_PIPELINE_COMPANY_NAME` — application/company name, default: `SEC Filings Pipeline`
- `SEC_PIPELINE_EMAIL` — contact email for SEC identification
- `SEC_PIPELINE_USER_AGENT` — optional full SEC user-agent string
- `SEC_PIPELINE_SLEEP_SECONDS` — delay between download requests, default: `0.15`

## Usage

Download latest 10-K filings:

```bash
sec-filings download --email you@example.com
```

Convert downloaded `.txt` filings to Markdown:

```bash
sec-filings parse
```

The parser writes `.md` files next to raw SEC `.txt` downloads. It prefers `sec2md` for conversion and falls back to the legacy generic HTML converter for unusual filings that `sec2md` cannot parse.

Run both steps:

```bash
sec-filings run --email you@example.com
```

## Development checks

```bash
python -m compileall src tests
python -m pytest
python -m ruff check .
```

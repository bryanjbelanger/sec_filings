"""Download SEC filing data."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests
from sec_edgar_downloader import Downloader

from sec_filings.config import PipelineConfig

LOGGER = logging.getLogger(__name__)
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def fetch_active_tickers(user_agent: str) -> list[str]:
    """Fetch active company tickers from the SEC ticker feed."""

    response = requests.get(TICKERS_URL, headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame.from_dict(response.json(), orient="index")
    return frame["ticker"].dropna().unique().tolist()


def download_latest_10k_for_tickers(config: PipelineConfig, tickers: list[str] | None = None) -> int:
    """Download the latest 10-K for each ticker and return attempted download count."""

    config.data_dir.mkdir(parents=True, exist_ok=True)
    user_agent = config.effective_user_agent
    active_tickers = tickers if tickers is not None else fetch_active_tickers(user_agent)
    downloader = Downloader(config.company_name, config.effective_email, str(config.data_dir))
    error_log = config.data_dir / "latest_download_errors.log"

    LOGGER.info("Loaded %s ticker(s) to process.", len(active_tickers))
    attempted = 0

    for index, ticker in enumerate(active_tickers, start=1):
        filing_dir = _filing_directory(config.data_dir, ticker)
        if _has_existing_download(filing_dir):
            continue

        attempted += 1
        LOGGER.info("[%s/%s] Fetching latest 10-K for %s", index, len(active_tickers), ticker)
        try:
            downloader.get("10-K", ticker, limit=1)
        except Exception as exc:  # noqa: BLE001 - external downloader raises broad exceptions
            _append_error(error_log, f"Error {ticker}: {exc}")
        finally:
            time.sleep(config.sleep_seconds)

    LOGGER.info("Finished latest 10-K download pass. Attempted %s download(s).", attempted)
    return attempted


def _filing_directory(data_dir: Path, ticker: str) -> Path:
    return data_dir / "sec-edgar-filings" / ticker / "10-K"


def _has_existing_download(filing_dir: Path) -> bool:
    return filing_dir.exists() and any(filing_dir.iterdir())


def _append_error(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")

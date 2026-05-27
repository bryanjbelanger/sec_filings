"""Command-line interface for the SEC filings pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sec_filings.config import PipelineConfig
from sec_filings.downloader import download_latest_10k_for_tickers
from sec_filings.parser import convert_filings_to_markdown


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="sec-filings",
        description="Download SEC 10-K filings and convert them to Markdown.",
    )
    parser.add_argument("--data-dir", type=Path, help="Base directory for downloaded filings.")
    parser.add_argument("--company-name", help="Company/application name for SEC identification.")
    parser.add_argument("--email", help="Contact email for SEC identification.")
    parser.add_argument("--user-agent", help="Full User-Agent header for SEC HTTP requests.")
    parser.add_argument("--sleep-seconds", type=float, help="Delay between SEC download requests.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_download_parser(subparsers)
    _add_parse_parser(subparsers)
    _add_run_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=args.verbose)
    config = PipelineConfig.from_environment().with_overrides(
        data_dir=args.data_dir,
        company_name=args.company_name,
        email=args.email,
        user_agent=args.user_agent,
        sleep_seconds=args.sleep_seconds,
    )

    if args.command == "download":
        download_latest_10k_for_tickers(config, tickers=args.tickers)
        return 0

    if args.command == "parse":
        convert_filings_to_markdown(
            config.data_dir,
            max_workers=args.max_workers,
            progress_interval=args.progress_interval,
        )
        return 0

    if args.command == "run":
        download_latest_10k_for_tickers(config, tickers=args.tickers)
        convert_filings_to_markdown(
            config.data_dir,
            max_workers=args.max_workers,
            progress_interval=args.progress_interval,
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_download_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    download_parser = subparsers.add_parser("download", help="Download latest 10-K filings.")
    download_parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="Ticker to download. Repeat to download multiple specific tickers.",
    )


def _add_parse_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parse_parser = subparsers.add_parser("parse", help="Convert downloaded filings to Markdown.")
    parse_parser.add_argument("--max-workers", type=int, help="Maximum parser worker processes.")
    parse_parser.add_argument(
        "--progress-interval",
        type=int,
        default=50,
        help="Completed files between progress log messages.",
    )


def _add_run_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    run_parser = subparsers.add_parser("run", help="Download filings and then convert them.")
    run_parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="Ticker to download. Repeat to download multiple specific tickers.",
    )
    run_parser.add_argument("--max-workers", type=int, help="Maximum parser worker processes.")
    run_parser.add_argument(
        "--progress-interval",
        type=int,
        default=50,
        help="Completed files between progress log messages.",
    )


def _configure_logging(*, verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

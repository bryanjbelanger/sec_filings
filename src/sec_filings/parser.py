"""Convert SEC filing documents to Markdown."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import html2text
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ParseSummary:
    """Summary of a filing conversion run."""

    total: int
    succeeded: int
    failed: int
    elapsed_seconds: float


def clean_and_convert_file(input_path: Path, output_path: Path) -> tuple[bool, str]:
    """Strip SEC boilerplate from one filing and convert it to Markdown."""

    try:
        raw_content = input_path.read_text(encoding="utf-8", errors="ignore")
        markdown_text = convert_filing_to_markdown(raw_content)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_text, encoding="utf-8")
        return True, str(input_path)
    except Exception as exc:  # noqa: BLE001 - worker reports all conversion failures
        return False, f"{input_path} -> {exc}"


def convert_filing_to_markdown(raw_content: str) -> str:
    """Convert raw SEC filing text/HTML into cleaned Markdown."""

    soup = BeautifulSoup(_strip_metadata_header(raw_content), "lxml")
    for element in soup(["script", "style", "textarea"]):
        element.decompose()

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = True
    converter.ignore_images = True
    converter.images_to_alt = False

    return _clean_markdown(converter.handle(str(soup)))


def find_unconverted_filings(base_dir: Path) -> list[tuple[Path, Path]]:
    """Return raw `.txt` filings that do not yet have matching Markdown files."""

    tasks: list[tuple[Path, Path]] = []
    for root, _, files in os.walk(base_dir):
        root_path = Path(root)
        for filename in files:
            input_path = root_path / filename
            if not _is_raw_text_filing(input_path):
                continue

            output_path = input_path.with_suffix(".md")
            if not output_path.exists():
                tasks.append((input_path, output_path))
    return tasks


def convert_filings_to_markdown(
    base_dir: Path,
    *,
    max_workers: int | None = None,
    progress_interval: int = 50,
) -> ParseSummary:
    """Convert all outstanding raw filing `.txt` files below `base_dir` to Markdown."""

    tasks = find_unconverted_filings(base_dir)
    total_tasks = len(tasks)
    if total_tasks == 0:
        LOGGER.info("No new files found to convert. Pipeline is already up to date.")
        return ParseSummary(total=0, succeeded=0, failed=0, elapsed_seconds=0.0)

    worker_count = max_workers if max_workers is not None else _default_worker_count()
    LOGGER.info("Found %s file(s) requiring conversion.", total_tasks)
    LOGGER.info("Starting conversion with %s worker(s).", worker_count)

    start_time = time.time()
    success_count = 0
    failure_count = 0
    error_log = base_dir / "parallel_parsing_errors.log"

    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(clean_and_convert_file, input_path, output_path): input_path
            for input_path, output_path in tasks
        }

        for completed_count, future in enumerate(as_completed(futures), start=1):
            success, meta = future.result()
            if success:
                success_count += 1
            else:
                failure_count += 1
                _append_errors(error_log, [meta])

            if completed_count % progress_interval == 0 or completed_count == total_tasks:
                pct = (completed_count / total_tasks) * 100
                LOGGER.info(
                    "Progress: [%s/%s] (%.1f%%) | Success: %s | Failed: %s",
                    completed_count,
                    total_tasks,
                    pct,
                    success_count,
                    failure_count,
                )

    elapsed_seconds = time.time() - start_time
    LOGGER.info("Finished Markdown conversion in %.2f minute(s).", elapsed_seconds / 60)
    return ParseSummary(total_tasks, success_count, failure_count, elapsed_seconds)


def _strip_metadata_header(raw_content: str) -> str:
    match = re.search(r"<DOCUMENT>", raw_content, re.IGNORECASE)
    return raw_content[match.start() :] if match else raw_content


def _clean_markdown(markdown_text: str) -> str:
    markdown_text = re.sub(r"^\s*(page\s+)?\d+\s*$", "", markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(
        r"(?i)^\s*table of contents\s*$", "", markdown_text, flags=re.MULTILINE
    )
    markdown_text = re.sub(r"(?i)^\s*index to.*$", "", markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r"\n\s*\n", "\n\n", markdown_text)
    return markdown_text.strip()


def _is_raw_text_filing(path: Path) -> bool:
    return path.suffix == ".txt" and not path.name.endswith("_cleaned.txt")


def _default_worker_count() -> int:
    return max(1, (os.cpu_count() or 1) - 2)


def _append_errors(log_path: Path, messages: Iterable[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        for message in messages:
            log_file.write(f"{message}\n")

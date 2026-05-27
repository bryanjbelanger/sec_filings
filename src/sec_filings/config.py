"""Configuration helpers for the SEC filings pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_COMPANY_NAME = "SEC Filings Pipeline"
DEFAULT_DATA_DIR = Path("/sec")
DEFAULT_SLEEP_SECONDS = 0.15


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Runtime configuration shared by downloader and parser commands."""

    data_dir: Path = DEFAULT_DATA_DIR
    company_name: str = DEFAULT_COMPANY_NAME
    email: str | None = None
    user_agent: str | None = None
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS

    @classmethod
    def from_environment(cls) -> "PipelineConfig":
        """Build configuration from environment variables."""

        return cls(
            data_dir=Path(os.getenv("SEC_PIPELINE_DATA_DIR", str(DEFAULT_DATA_DIR))),
            company_name=os.getenv("SEC_PIPELINE_COMPANY_NAME", DEFAULT_COMPANY_NAME),
            email=os.getenv("SEC_PIPELINE_EMAIL"),
            user_agent=os.getenv("SEC_PIPELINE_USER_AGENT"),
            sleep_seconds=float(os.getenv("SEC_PIPELINE_SLEEP_SECONDS", DEFAULT_SLEEP_SECONDS)),
        )

    def with_overrides(
        self,
        *,
        data_dir: Path | None = None,
        company_name: str | None = None,
        email: str | None = None,
        user_agent: str | None = None,
        sleep_seconds: float | None = None,
    ) -> "PipelineConfig":
        """Return a new config with explicit CLI overrides applied."""

        return PipelineConfig(
            data_dir=data_dir if data_dir is not None else self.data_dir,
            company_name=company_name if company_name is not None else self.company_name,
            email=email if email is not None else self.email,
            user_agent=user_agent if user_agent is not None else self.user_agent,
            sleep_seconds=sleep_seconds if sleep_seconds is not None else self.sleep_seconds,
        )

    @property
    def effective_email(self) -> str:
        """Return a configured SEC contact email or raise a clear error."""

        if not self.email:
            msg = "Set SEC_PIPELINE_EMAIL or pass --email you@example.com before downloading."
            raise ValueError(msg)
        return self.email

    @property
    def effective_user_agent(self) -> str:
        """Return a SEC-compliant user agent string."""

        if self.user_agent:
            return self.user_agent
        return f"{self.company_name} contact {self.effective_email}"

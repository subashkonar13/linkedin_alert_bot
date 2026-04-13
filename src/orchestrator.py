"""
Orchestrator — Central coordinator for the full alert-creation pipeline.

Responsibilities:
- Skip already-completed alerts (via StateTracker)
- Retry failed alerts with backoff (via RetryEngine)
- Delegate per-company alert creation to JobAlertCreator
- Record results back into state
"""

from selenium.webdriver.chrome.webdriver import WebDriver
from src.alert_creator import JobAlertCreator, AlertResult
from src.state_tracker import StateTracker
from src.retry_engine import RetryEngine
from src.config_loader import CompaniesConfig
from src.logger import get_logger

logger = get_logger(__name__)


class AlertOrchestrator:

    def __init__(
        self,
        driver: WebDriver,
        companies_config: CompaniesConfig,
        delay_seconds: int = 4,
        max_retries: int = 3,
        location_filter: str = None,
        retry_failed_only: bool = False
    ):
        self.creator = JobAlertCreator(driver, companies_config.job_title, delay_seconds)
        self.companies_config = companies_config
        self.state = StateTracker()
        self.retry_engine = RetryEngine(max_attempts=max_retries)
        self.location_filter = location_filter
        self.retry_failed_only = retry_failed_only

    def run(self) -> list[AlertResult]:
        """
        Main execution loop.
        Iterates locations → companies, skipping already successful ones.
        """
        all_results: list[AlertResult] = []

        if self.retry_failed_only:
            return self._retry_previous_failures()

        for location, companies in self.companies_config.locations.items():
            if self.location_filter and location != self.location_filter:
                continue
            if not companies:
                logger.info(f"Skipping {location} — no companies listed.")
                continue

            logger.info(f"\n📍 {location}  ({len(companies)} companies)")
            results = self._process_location(location, companies)
            all_results.extend(results)

        return all_results

    def _process_location(self, location: str, companies: list[str]) -> list[AlertResult]:
        results = []
        for company in companies:
            if self.state.is_done(company, location):
                logger.info(f"  ⏭  Skipping [{company}] — already set.")
                results.append(AlertResult(company, location, "skipped", "Already set"))
                continue

            result, _ = self.retry_engine.run(
                self.creator._create_alert, company, location
            )

            if result is None:
                result = AlertResult(company, location, "failed", "Retry exhausted")

            self.state.mark(result.company, result.location, result.status, result.reason)
            results.append(result)

        return results

    def _retry_previous_failures(self) -> list[AlertResult]:
        """Re-processes only entries that previously failed."""
        failed_pairs = self.state.get_failed()
        if not failed_pairs:
            logger.info("No previously failed alerts to retry.")
            return []

        logger.info(f"Retrying {len(failed_pairs)} previously failed alerts...")
        results = []
        for company, location in failed_pairs:
            result, _ = self.retry_engine.run(
                self.creator._create_alert, company, location
            )
            if result is None:
                result = AlertResult(company, location, "failed", "Retry exhausted")
            self.state.mark(result.company, result.location, result.status, result.reason)
            results.append(result)

        return results

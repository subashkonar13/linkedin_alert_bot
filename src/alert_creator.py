import time
import urllib.parse
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AlertResult:
    company: str
    location: str
    status: str          # "success" | "failed" | "skipped"
    reason: str = ""


class JobAlertCreator:
    """
    Core module that navigates LinkedIn job search for each company+location
    pair and enables the job alert toggle.

    Responsibilities:
    - Build LinkedIn job search URL with keyword + location filters
    - Apply company name filter
    - Click the "Set Alert" button
    - Return structured results per company
    """

    JOBS_BASE_URL = "https://www.linkedin.com/jobs/search/"

    def __init__(self, driver: WebDriver, job_title: str, delay_seconds: int = 4):
        self.driver = driver
        self.job_title = job_title
        self.delay = delay_seconds
        self.wait = WebDriverWait(driver, 10)

    def create_alerts_for_location(
        self, location: str, companies: list[str]
    ) -> list[AlertResult]:
        """
        Iterates through companies for a given location and sets a job alert for each.
        """
        results = []
        for company in companies:
            logger.info(f"  → Setting alert: [{location}] {company}")
            result = self._create_alert(company, location)
            results.append(result)
            time.sleep(self.delay)
        return results

    def _create_alert(self, company: str, location: str) -> AlertResult:
        """Navigate to a company+location job search and toggle the alert on."""
        try:
            url = self._build_search_url(self.job_title, location)
            self.driver.get(url)
            time.sleep(3)

            # Apply company filter via the search filter UI
            applied = self._apply_company_filter(company)
            if not applied:
                return AlertResult(company, location, "failed", "Could not apply company filter")

            # Click alert toggle
            alerted = self._toggle_alert()
            if alerted:
                return AlertResult(company, location, "success")
            else:
                return AlertResult(company, location, "failed", "Alert toggle not found or already set")

        except Exception as e:
            logger.error(f"Unexpected error for {company} @ {location}: {e}")
            return AlertResult(company, location, "failed", str(e))

    def _build_search_url(self, job_title: str, location: str) -> str:
        params = urllib.parse.urlencode({
            "keywords": job_title,
            "location": location,
            "origin": "JOB_SEARCH_PAGE_SEARCH_BUTTON"
        })
        return f"{self.JOBS_BASE_URL}?{params}"

    def _apply_company_filter(self, company: str) -> bool:
        """Clicks the Company filter and types the company name."""
        try:
            # Click "Company" filter button
            company_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'Company') or .//span[text()='Company']]")
                )
            )
            company_btn.click()
            time.sleep(1.5)

            # Type company name in the filter search box
            filter_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@placeholder, 'company') or contains(@aria-label, 'company')]")
                )
            )
            filter_input.clear()
            filter_input.send_keys(company)
            time.sleep(2)

            # Select the first matching result
            first_result = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class,'search-typeahead')]//li[1] | //ul[@role='listbox']//li[1]")
                )
            )
            first_result.click()
            time.sleep(1)

            # Apply/confirm the filter
            try:
                show_results_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(),'Show') or contains(@aria-label,'Apply')]"
                )
                show_results_btn.click()
                time.sleep(2)
            except NoSuchElementException:
                pass  # Some UI versions auto-apply the filter

            return True

        except TimeoutException:
            logger.warning(f"Company filter not available for: {company}")
            return False

    def _toggle_alert(self) -> bool:
        """Finds and clicks the job alert toggle/button in search results."""
        selectors = [
            "//button[contains(@aria-label, 'Alert')]",
            "//button[contains(., 'Set alert')]",
            "//button[contains(., 'Create job alert')]",
            "//*[@data-control-name='alert_toggle']",
        ]
        for selector in selectors:
            try:
                btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                btn.click()
                time.sleep(2)
                logger.info("    ✅ Alert toggled ON.")
                return True
            except TimeoutException:
                continue

        logger.warning("    ⚠️  Alert button not found. May already be set or UI changed.")
        return False

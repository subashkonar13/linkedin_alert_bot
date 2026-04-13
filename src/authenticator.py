import json
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.otp_fetcher import GmailOTPFetcher
from src.logger import get_logger

logger = get_logger(__name__)


class LinkedInAuthenticator:
    """
    Handles LinkedIn authentication with three strategies:
    1. Cookie-based login (primary — bypasses 2FA)
    2. Credential login + Gmail OTP auto-fetch (fallback)
    3. Manual login with wait (last resort)
    """

    LOGIN_URL = "https://www.linkedin.com/login"
    FEED_URL = "https://www.linkedin.com/feed"

    def __init__(
        self,
        driver: WebDriver,
        email: str,
        password: str,
        cookie_path: str = "config/cookies.json",
        otp_fetcher: GmailOTPFetcher = None
    ):
        self.driver = driver
        self.email = email
        self.password = password
        self.cookie_path = cookie_path
        self.otp_fetcher = otp_fetcher
        self.wait = WebDriverWait(driver, 15)

    # ------------------------------------------------------------------ #
    # PUBLIC: Primary entry point
    # ------------------------------------------------------------------ #

    def login(self) -> bool:
        """
        Attempts login using cookie session first.
        Falls back to credential login + OTP if cookies are expired.
        """
        if os.path.exists(self.cookie_path):
            logger.info("Cookie file found — attempting cookie-based login.")
            if self._login_with_cookies():
                return True
            logger.warning("Cookie login failed. Falling back to credential login.")

        return self._login_with_credentials()

    # ------------------------------------------------------------------ #
    # STRATEGY 1: Cookie-based login
    # ------------------------------------------------------------------ #

    def save_cookies(self, manual_wait_seconds: int = 90) -> None:
        """
        ONE-TIME SETUP: Opens LinkedIn login page and waits for manual login.
        After you complete login + 2FA, cookies are saved automatically.

        Run this once when setting up or when cookies expire.
        """
        logger.info("Opening LinkedIn for manual login (run this once to save cookies)...")
        self.driver.get(self.LOGIN_URL)
        logger.info(
            f"Please log in manually in the browser window "
            f"(complete 2FA if prompted). Waiting {manual_wait_seconds}s..."
        )
        time.sleep(manual_wait_seconds)

        if "feed" in self.driver.current_url or "checkpoint" not in self.driver.current_url:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Cookies saved to: {self.cookie_path}")
        else:
            logger.error("Login did not complete within the wait window. Please retry.")

    def _login_with_cookies(self) -> bool:
        """Loads saved cookies into the browser session to skip login."""
        try:
            self.driver.get("https://www.linkedin.com")
            time.sleep(2)

            with open(self.cookie_path) as f:
                cookies = json.load(f)

            for cookie in cookies:
                cookie.pop("sameSite", None)  # Avoid Selenium cookie errors
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass  # Some cookies may be rejected — that's fine

            self.driver.refresh()
            time.sleep(3)

            if self._is_logged_in():
                logger.info("Cookie-based login successful.")
                return True

            logger.warning("Cookies present but session has expired.")
            return False

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Cookie file issue: {e}")
            return False

    # ------------------------------------------------------------------ #
    # STRATEGY 2: Credential login + Gmail OTP
    # ------------------------------------------------------------------ #

    def _login_with_credentials(self) -> bool:
        """Submits email/password and handles 2FA via Gmail OTP fetcher."""
        try:
            logger.info("Attempting credential-based login...")
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)

            self.driver.find_element(By.ID, "username").send_keys(self.email)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(4)

            # Check if 2FA is triggered
            if self._is_2fa_page():
                logger.info("2FA challenge detected.")
                if not self._handle_2fa():
                    return False

            if self._is_logged_in():
                self._persist_cookies()
                logger.info("Credential login successful. Cookies saved.")
                return True

            logger.error("Login failed after credential submission.")
            return False

        except Exception as e:
            logger.error(f"Credential login error: {e}")
            return False

    def _handle_2fa(self) -> bool:
        """Fetches OTP from Gmail and submits it on the 2FA page."""
        if not self.otp_fetcher:
            logger.warning(
                "No OTP fetcher configured. "
                "Waiting 60s for manual OTP entry..."
            )
            time.sleep(60)
            return self._is_logged_in()

        otp = self.otp_fetcher.fetch_otp()
        if not otp:
            logger.error("Could not retrieve OTP from Gmail.")
            return False

        try:
            otp_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@id='input__phone_verification_pin' or @name='pin']")
                )
            )
            otp_input.clear()
            otp_input.send_keys(otp)
            time.sleep(1)

            submit_btn = self.driver.find_element(
                By.XPATH,
                "//button[@id='two-step-submit-button' or @type='submit']"
            )
            submit_btn.click()
            time.sleep(4)
            logger.info("OTP submitted successfully.")
            return True

        except Exception as e:
            logger.error(f"OTP submission failed: {e}")
            return False

    # ------------------------------------------------------------------ #
    # HELPERS
    # ------------------------------------------------------------------ #

    def _is_logged_in(self) -> bool:
        return "feed" in self.driver.current_url or (
            "linkedin.com" in self.driver.current_url
            and "login" not in self.driver.current_url
            and "checkpoint" not in self.driver.current_url
        )

    def _is_2fa_page(self) -> bool:
        return (
            "checkpoint" in self.driver.current_url
            or "verification" in self.driver.current_url
            or "two-step" in self.driver.page_source.lower()
        )

    def _persist_cookies(self) -> None:
        os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
        with open(self.cookie_path, "w") as f:
            json.dump(self.driver.get_cookies(), f, indent=2)

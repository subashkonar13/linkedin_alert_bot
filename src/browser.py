from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.logger import get_logger

logger = get_logger(__name__)


class BrowserFactory:
    """
    Responsible for creating and configuring the Selenium WebDriver.
    Follows Single Responsibility Principle — only handles browser setup.
    """

    @staticmethod
    def get_driver(headless: bool = False) -> webdriver.Chrome:
        options = Options()

        if headless:
            options.add_argument("--headless=new")

        # Stealth settings to reduce bot detection
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1280,900")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.implicitly_wait(6)
        logger.info("Browser initialized successfully.")
        return driver

    @staticmethod
    def quit_driver(driver: webdriver.Chrome) -> None:
        try:
            driver.quit()
            logger.info("Browser closed.")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

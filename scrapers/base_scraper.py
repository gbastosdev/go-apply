import asyncio
import shutil
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from utils.logger import setup_logger
from services.tech_stack_extractor import TechStackExtractor

logger = setup_logger(__name__)


class BaseScraper(ABC):
    TIMEOUT = 30  # seconds (selenium uses seconds, not ms)
    MAX_RETRIES = 3
    COMPANY_NAME = "unknown"

    def __init__(self):
        self.tech_extractor = TechStackExtractor()

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        pass

    async def scrape_with_retry(self) -> List[Dict]:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"{self.COMPANY_NAME}: Starting scrape attempt {attempt}/{self.MAX_RETRIES}")
                jobs = await self.scrape()
                logger.info(f"{self.COMPANY_NAME}: Successfully scraped {len(jobs)} jobs")
                return jobs
            except Exception as e:
                logger.error(f"{self.COMPANY_NAME}: Error on attempt {attempt}: {e}")
                if attempt == self.MAX_RETRIES:
                    logger.error(f"{self.COMPANY_NAME}: All retries exhausted")
                    raise
                await asyncio.sleep(5 * attempt)
        return []

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # Locate system chromium (Railway apt-installed)
        chromium = shutil.which("chromium-browser") or shutil.which("chromium")
        if chromium:
            options.binary_location = chromium
        return webdriver.Chrome(options=options)

    def safe_get_text(self, driver: webdriver.Chrome, selector: str, default: str = "") -> str:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            return el.text.strip() or default
        except Exception:
            return default

    def generate_job_id(self, title: str, company: str) -> str:
        sanitized = "".join(c.lower() if c.isalnum() else "_" for c in title)
        sanitized = "_".join(filter(None, sanitized.split("_")))[:50]
        hash_short = hashlib.md5(f"{company}_{title}".encode()).hexdigest()[:8]
        return f"{company}_{sanitized}_{hash_short}"

    def extract_tech_stack(self, text: str) -> List[str]:
        return self.tech_extractor.extract(text)

    def create_job_dict(
        self,
        title: str,
        requirements: List[str],
        location: str,
        url: str,
        posting_date: str = None,
        description: str = None,
    ) -> Dict:
        tech_text = description if description else " ".join(requirements)
        return {
            "id": self.generate_job_id(title, self.COMPANY_NAME),
            "company": self.COMPANY_NAME,
            "title": title,
            "requirements": requirements,
            "location": location,
            "posting_date": posting_date,
            "tech_stack": self.extract_tech_stack(tech_text),
            "url": url,
            "scraped_at": datetime.now(),
        }

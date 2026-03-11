import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict

from camoufox.sync_api import Camoufox

from utils.logger import setup_logger
from services.tech_stack_extractor import TechStackExtractor

logger = setup_logger(__name__)


class BaseScraper(ABC):
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

    def _browser(self) -> Camoufox:
        """Return a configured Camoufox context manager."""
        return Camoufox(headless=True)

    def extract_tech_stack(self, text: str) -> List[str]:
        return self.tech_extractor.extract(text)

    def generate_job_id(self, title: str, company: str) -> str:
        sanitized = "".join(c.lower() if c.isalnum() else "_" for c in title)
        sanitized = "_".join(filter(None, sanitized.split("_")))[:50]
        hash_short = hashlib.md5(f"{company}_{title}".encode()).hexdigest()[:8]
        return f"{company}_{sanitized}_{hash_short}"

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
        tech_stack = self.extract_tech_stack(tech_text)
        # Combine requirements + tech keywords into one searchable `skills` list.
        skills = list(dict.fromkeys(requirements + tech_stack))
        return {
            "id": self.generate_job_id(title, self.COMPANY_NAME),
            "company": self.COMPANY_NAME,
            "title": title,
            "skills": skills,
            "location": location,
            "posting_date": posting_date,
            "url": url,
            "scraped_at": datetime.now(),
        }

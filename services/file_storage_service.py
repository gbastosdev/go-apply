import os
import json
import asyncio
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger(__name__)


class FileStorageService:
    """
    Simple file-based storage for job opportunities

    Stores all job data in a single JSON file for simplicity
    """

    def __init__(self):
        self.storage_dir = Path("data")
        self.jobs_file = self.storage_dir / "jobs.json"
        self.lock_file = self.storage_dir / "scrape.lock"

        # Create data directory if it doesn't exist
        self.storage_dir.mkdir(exist_ok=True)

        # Initialize empty storage if file doesn't exist
        if not self.jobs_file.exists():
            self._write_data({
                "jobs": [],
                "metadata": {
                    "total_count": 0,
                    "cached_at": datetime.now().isoformat(),
                    "companies": {}
                }
            })

    async def connect(self):
        """Placeholder for compatibility with Redis service"""
        logger.info(f"File storage initialized at {self.storage_dir.absolute()}")

    async def disconnect(self):
        """Placeholder for compatibility with Redis service"""
        logger.info("File storage closed")

    def _read_data(self) -> Dict:
        """Read data from JSON file"""
        try:
            with open(self.jobs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading jobs file: {e}")
            return {"jobs": [], "metadata": {"total_count": 0, "cached_at": datetime.now().isoformat(), "companies": {}}}

    def _write_data(self, data: Dict):
        """Write data to JSON file"""
        try:
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error writing jobs file: {e}")
            raise

    # ============= Job Operations =============

    async def set_all_jobs(self, jobs: List[Dict]) -> None:
        """Store all jobs in file"""
        try:
            data = self._read_data()
            data["jobs"] = jobs
            data["metadata"]["total_count"] = len(jobs)
            data["metadata"]["cached_at"] = datetime.now().isoformat()

            self._write_data(data)
            logger.info(f"Stored {len(jobs)} jobs to file")
        except Exception as e:
            logger.error(f"Error storing all jobs: {e}")
            raise

    async def get_all_jobs(self) -> Optional[List[Dict]]:
        """Retrieve all jobs from file"""
        try:
            data = self._read_data()
            return data.get("jobs", [])
        except Exception as e:
            logger.error(f"Error retrieving all jobs: {e}")
            return []

    async def set_company_jobs(self, company: str, jobs: List[Dict]) -> None:
        """Store jobs for a specific company (updates the main jobs list)"""
        try:
            data = self._read_data()

            # Remove old jobs from this company
            existing_jobs = [j for j in data.get("jobs", []) if j.get("company") != company]

            # Add new jobs
            existing_jobs.extend(jobs)

            data["jobs"] = existing_jobs
            data["metadata"]["total_count"] = len(existing_jobs)

            self._write_data(data)
            logger.info(f"Updated {len(jobs)} jobs for {company}")
        except Exception as e:
            logger.error(f"Error storing jobs for {company}: {e}")

    async def get_company_jobs(self, company: str) -> Optional[List[Dict]]:
        """Retrieve jobs for a specific company"""
        try:
            data = self._read_data()
            company_jobs = [j for j in data.get("jobs", []) if j.get("company") == company]
            return company_jobs if company_jobs else None
        except Exception as e:
            logger.error(f"Error retrieving jobs for {company}: {e}")
            return None

    # ============= Metadata Operations =============

    async def set_metadata(self, metadata: Dict) -> None:
        """Store metadata about scraping results"""
        try:
            data = self._read_data()
            data["metadata"] = metadata
            self._write_data(data)
            logger.info("Stored metadata")
        except Exception as e:
            logger.error(f"Error storing metadata: {e}")

    async def get_metadata(self) -> Dict:
        """Retrieve scraping metadata"""
        try:
            data = self._read_data()
            return data.get("metadata", {
                "total_count": 0,
                "cached_at": datetime.now().isoformat(),
                "companies": {}
            })
        except Exception as e:
            logger.error(f"Error retrieving metadata: {e}")
            return {"total_count": 0, "cached_at": datetime.now().isoformat(), "companies": {}}

    async def set_scrape_status(self, company: str, status: str, job_count: int, error: Optional[str] = None) -> None:
        """Update scraping status for a company"""
        try:
            data = self._read_data()

            if "metadata" not in data:
                data["metadata"] = {"companies": {}}
            if "companies" not in data["metadata"]:
                data["metadata"]["companies"] = {}

            data["metadata"]["companies"][company] = {
                "last_scraped": datetime.now().isoformat(),
                "status": status,
                "count": job_count,
                "error": error
            }

            self._write_data(data)
            logger.info(f"Updated status for {company}: {status}")
        except Exception as e:
            logger.error(f"Error setting status for {company}: {e}")

    async def get_scrape_status(self, company: str) -> Optional[Dict]:
        """Get scraping status for a company"""
        try:
            data = self._read_data()
            companies = data.get("metadata", {}).get("companies", {})
            return companies.get(company)
        except Exception as e:
            logger.error(f"Error getting status for {company}: {e}")
            return None

    # ============= Lock Operations =============

    async def acquire_scrape_lock(self) -> bool:
        """
        Acquire lock for scraping using a lock file
        Returns True if lock acquired, False if already locked
        """
        try:
            if self.lock_file.exists():
                # Check if lock is stale (older than 1 hour)
                lock_age = datetime.now().timestamp() - self.lock_file.stat().st_mtime
                if lock_age > 3600:  # 1 hour
                    logger.warning("Stale lock detected, removing")
                    self.lock_file.unlink()
                else:
                    logger.warning("Scrape lock already held, skipping")
                    return False

            # Create lock file
            self.lock_file.touch()
            logger.info("Scrape lock acquired")
            return True
        except Exception as e:
            logger.error(f"Error acquiring scrape lock: {e}")
            return False

    async def release_scrape_lock(self) -> None:
        """Release lock for scraping"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.info("Scrape lock released")
        except Exception as e:
            logger.error(f"Error releasing scrape lock: {e}")

    # ============= Utility Operations =============

    async def clear_all(self) -> None:
        """Clear all job data (useful for testing)"""
        try:
            self._write_data({
                "jobs": [],
                "metadata": {
                    "total_count": 0,
                    "cached_at": datetime.now().isoformat(),
                    "companies": {}
                }
            })
            logger.info("Cleared all data")
        except Exception as e:
            logger.error(f"Error clearing data: {e}")


# Singleton instance
file_storage = FileStorageService()

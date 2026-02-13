import os
import json
import redis.asyncio as redis
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class CacheService:
    """
    Async Redis cache service for job opportunities

    Key Structure:
    - jobs:all -> JSON string of all jobs
    - jobs:metadata -> JSON with cached_at, total_count, companies_status
    - jobs:company:{company_name} -> JSON string of jobs for specific company
    - jobs:last_scrape:{company_name} -> Timestamp of last successful scrape
    - jobs:errors:{company_name} -> JSON of last error if scrape failed
    - jobs:scrape_lock -> Distributed lock to prevent concurrent scrapes
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.ttl = 86400  # 24 hours in seconds

    async def connect(self):
        """Establish Redis connection on application startup"""
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD", None)

        try:
            self.redis = await redis.from_url(
                f"redis://{host}:{port}/{db}",
                password=password,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info(f"Redis connected successfully at {host}:{port}/{db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection on application shutdown"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    # ============= Job Operations =============

    async def set_all_jobs(self, jobs: List[Dict]) -> None:
        """Store all jobs in cache with TTL"""
        try:
            jobs_json = json.dumps(jobs)
            await self.redis.setex("jobs:all", self.ttl, jobs_json)
            logger.info(f"Cached {len(jobs)} jobs with {self.ttl}s TTL")
        except Exception as e:
            logger.error(f"Error caching all jobs: {e}")
            raise

    async def get_all_jobs(self) -> Optional[List[Dict]]:
        """Retrieve all jobs from cache"""
        try:
            jobs_json = await self.redis.get("jobs:all")
            if jobs_json:
                return json.loads(jobs_json)
            return None
        except Exception as e:
            logger.error(f"Error retrieving all jobs: {e}")
            return None

    async def set_company_jobs(self, company: str, jobs: List[Dict]) -> None:
        """Store jobs for a specific company"""
        try:
            key = f"jobs:company:{company}"
            jobs_json = json.dumps(jobs)
            await self.redis.setex(key, self.ttl, jobs_json)
            logger.info(f"Cached {len(jobs)} jobs for {company}")
        except Exception as e:
            logger.error(f"Error caching jobs for {company}: {e}")

    async def get_company_jobs(self, company: str) -> Optional[List[Dict]]:
        """Retrieve jobs for a specific company"""
        try:
            key = f"jobs:company:{company}"
            jobs_json = await self.redis.get(key)
            if jobs_json:
                return json.loads(jobs_json)
            return None
        except Exception as e:
            logger.error(f"Error retrieving jobs for {company}: {e}")
            return None

    # ============= Metadata Operations =============

    async def set_metadata(self, metadata: Dict) -> None:
        """Store metadata about scraping results"""
        try:
            metadata_json = json.dumps(metadata, default=str)
            await self.redis.setex("jobs:metadata", self.ttl, metadata_json)
            logger.info("Cached jobs metadata")
        except Exception as e:
            logger.error(f"Error caching metadata: {e}")

    async def get_metadata(self) -> Dict:
        """Retrieve scraping metadata"""
        try:
            metadata_json = await self.redis.get("jobs:metadata")
            if metadata_json:
                return json.loads(metadata_json)
            return {
                "total_count": 0,
                "filtered_count": 0,
                "cached_at": datetime.now().isoformat(),
                "companies": {}
            }
        except Exception as e:
            logger.error(f"Error retrieving metadata: {e}")
            return {"total_count": 0, "filtered_count": 0, "cached_at": datetime.now().isoformat(), "companies": {}}

    async def set_scrape_status(self, company: str, status: str, job_count: int, error: Optional[str] = None) -> None:
        """Update scraping status for a company"""
        try:
            status_data = {
                "last_scraped": datetime.now().isoformat(),
                "status": status,
                "job_count": job_count,
                "error": error
            }
            key = f"jobs:status:{company}"
            status_json = json.dumps(status_data)
            await self.redis.setex(key, self.ttl, status_json)
            logger.info(f"Updated status for {company}: {status}")
        except Exception as e:
            logger.error(f"Error setting status for {company}: {e}")

    async def get_scrape_status(self, company: str) -> Optional[Dict]:
        """Get scraping status for a company"""
        try:
            key = f"jobs:status:{company}"
            status_json = await self.redis.get(key)
            if status_json:
                return json.loads(status_json)
            return None
        except Exception as e:
            logger.error(f"Error getting status for {company}: {e}")
            return None

    # ============= Lock Operations =============

    async def acquire_scrape_lock(self) -> bool:
        """
        Acquire distributed lock for scraping
        Returns True if lock acquired, False if already locked
        """
        try:
            lock_key = "jobs:scrape_lock"
            # NX = only set if not exists, EX = expire in seconds
            locked = await self.redis.set(lock_key, "locked", nx=True, ex=3600)
            if locked:
                logger.info("Scrape lock acquired")
                return True
            else:
                logger.warning("Scrape lock already held, skipping")
                return False
        except Exception as e:
            logger.error(f"Error acquiring scrape lock: {e}")
            return False

    async def release_scrape_lock(self) -> None:
        """Release distributed lock for scraping"""
        try:
            await self.redis.delete("jobs:scrape_lock")
            logger.info("Scrape lock released")
        except Exception as e:
            logger.error(f"Error releasing scrape lock: {e}")

    # ============= Utility Operations =============

    async def clear_all(self) -> None:
        """Clear all job-related cache (useful for testing)"""
        try:
            keys = await self.redis.keys("jobs:*")
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


# Singleton instance
cache_service = CacheService()

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from utils.logger import setup_logger
from services.file_storage_service import file_storage
from scrapers.posthog_scraper import PostHogScraper
from scrapers.kraken_scraper import KrakenScraper
from scrapers.coinbase_scraper import CoinbaseScraper
from scrapers.railway_scraper import RailwayScraper
from scrapers.airbnb_scraper import AirbnbScraper

logger = setup_logger(__name__)


# Company scrapers registry
SCRAPERS = {
    "posthog": PostHogScraper,
    "kraken": KrakenScraper,
    "coinbase": CoinbaseScraper,
    "railway": RailwayScraper,
    "airbnb": AirbnbScraper
}


async def scrape_all_jobs():
    """
    Main scraping orchestrator - scrapes all companies in parallel

    Features:
    - Parallel scraping (all companies simultaneously)
    - Distributed lock to prevent concurrent runs
    - Partial failure handling (one company failing doesn't affect others)
    - Cache updates per company
    """
    logger.info("=" * 60)
    logger.info("Starting scheduled job scraping")
    logger.info("=" * 60)

    # Acquire distributed lock
    lock_acquired = await file_storage.acquire_scrape_lock()
    if not lock_acquired:
        logger.warning("Scrape already in progress, skipping this run")
        return

    try:
        start_time = datetime.now()
        all_jobs = []
        company_metadata = {}

        # Create scraping tasks for all companies (parallel execution)
        scraping_tasks = []
        for company_name, scraper_class in SCRAPERS.items():
            scraping_tasks.append(scrape_company(company_name, scraper_class))

        # Execute all scraping tasks in parallel
        results = await asyncio.gather(*scraping_tasks, return_exceptions=True)

        # Process results
        for company_name, result in zip(SCRAPERS.keys(), results):
            if isinstance(result, Exception):
                # Scraping failed for this company
                logger.error(f"Failed to scrape {company_name}: {result}")
                await file_storage.set_scrape_status(company_name, "failed", 0, str(result))

                # Try to get old cached data for this company
                old_jobs = await file_storage.get_company_jobs(company_name)
                if old_jobs:
                    all_jobs.extend(old_jobs)
                    logger.info(f"Using {len(old_jobs)} cached jobs from previous scrape for {company_name}")

                company_metadata[company_name] = {
                    "count": len(old_jobs) if old_jobs else 0,
                    "last_scraped": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(result)
                }
            else:
                # Scraping succeeded
                jobs = result
                all_jobs.extend(jobs)

                # Update storage for this company
                await file_storage.set_company_jobs(company_name, jobs)
                await file_storage.set_scrape_status(company_name, "success", len(jobs), None)

                company_metadata[company_name] = {
                    "count": len(jobs),
                    "last_scraped": datetime.now().isoformat(),
                    "status": "success",
                    "error": None
                }

                logger.info(f"Successfully scraped {len(jobs)} jobs from {company_name}")

        # Update main storage with all jobs
        await file_storage.set_all_jobs(all_jobs)

        # Update metadata
        metadata = {
            "total_count": len(all_jobs),
            "filtered_count": len(all_jobs),
            "cached_at": datetime.now().isoformat(),
            "companies": company_metadata
        }
        await file_storage.set_metadata(metadata)

        # Log summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"Scraping complete in {duration:.2f}s")
        logger.info(f"Total jobs scraped: {len(all_jobs)}")
        logger.info(f"Companies succeeded: {sum(1 for m in company_metadata.values() if m['status'] == 'success')}/{len(SCRAPERS)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Unexpected error during scraping: {e}")
    finally:
        # Always release the lock
        await file_storage.release_scrape_lock()


async def scrape_company(company_name: str, scraper_class) -> list:
    """
    Scrape a single company

    Args:
        company_name: Company name
        scraper_class: Scraper class to instantiate

    Returns:
        List of jobs (or raises exception on failure)
    """
    logger.info(f"Starting scrape for {company_name}")
    scraper = scraper_class()
    jobs = await scraper.scrape_with_retry()
    logger.info(f"Completed scrape for {company_name}: {len(jobs)} jobs")
    return jobs


class SchedulerService:
    """
    APScheduler service for periodic job scraping

    Configured to run at 6:00 AM Brazil time (America/Sao_Paulo) every day
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Sao_Paulo'))
        self.running = False

    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        # Schedule daily job at 6:00 AM Brazil time
        self.scheduler.add_job(
            scrape_all_jobs,
            trigger=CronTrigger(hour=6, minute=0),
            id='daily_job_scrape',
            name='Daily Job Scraping',
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs
            misfire_grace_time=3600  # If missed, run within 1 hour
        )

        self.scheduler.start()
        self.running = True

        logger.info("Scheduler started successfully")
        logger.info("Next scheduled run: 6:00 AM Brazil time (America/Sao_Paulo)")

        # Log next run time
        next_run = self.scheduler.get_job('daily_job_scrape').next_run_time
        logger.info(f"Next run at: {next_run}")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.running = False
            logger.info("Scheduler stopped")

    def get_status(self) -> dict:
        """Get scheduler status"""
        if not self.running:
            return {"running": False, "next_run": None}

        job = self.scheduler.get_job('daily_job_scrape')
        if job:
            return {
                "running": True,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
        return {"running": self.running, "next_run": None}


# Singleton instance
scheduler_service = SchedulerService()

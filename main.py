from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes
from services.file_storage_service import file_storage
from services.scheduler_service import scheduler_service
from utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events:
    - Startup: Initialize file storage, start scheduler
    - Shutdown: Stop scheduler, close file storage
    """
    # Startup
    logger.info("=" * 60)
    logger.info("GoApply starting up...")
    logger.info("=" * 60)

    try:
        # Initialize file storage
        await file_storage.connect()
        logger.info("[OK] File storage initialized")

        # Start scheduler
        scheduler_service.start()
        logger.info("[OK] Scheduler started")

        logger.info("=" * 60)
        logger.info("GoApply is ready!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("=" * 60)
    logger.info("GoApply shutting down...")
    logger.info("=" * 60)

    try:
        # Stop scheduler
        scheduler_service.stop()
        logger.info("[OK] Scheduler stopped")

        # Close file storage
        await file_storage.disconnect()
        logger.info("[OK] File storage closed")

        logger.info("=" * 60)
        logger.info("GoApply shut down successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
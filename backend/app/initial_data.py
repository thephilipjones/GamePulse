import logging

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Database engine initialized")
    # No initial data needed for public read-only dashboard
    logger.info("Initial data script completed")


if __name__ == "__main__":
    main()

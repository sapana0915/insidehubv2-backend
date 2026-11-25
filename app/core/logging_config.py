import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

# Example AI line:
# 2026-09-30 18:29:42: {user_id}- SUCCESS Tech AI generated
LOG_FORMAT = "%(asctime)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUPS = 5
CONSOLE_HANDLER = "insidehub-console"
FILE_HANDLER = "insidehub-file"
AI_FILE_HANDLER = "insidehub-ai-file"
AI_LOGGER_NAME = "app.insidehubv2_ai"


class ExcludeAIFilter(logging.Filter):
    """Keep AI module logs out of app.log (they go to ai.log instead)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith(AI_LOGGER_NAME)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    existing = {handler.get_name() for handler in root.handlers}
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    if CONSOLE_HANDLER not in existing:
        console = logging.StreamHandler()
        console.set_name(CONSOLE_HANDLER)
        console.setFormatter(formatter)
        root.addHandler(console)

    if FILE_HANDLER not in existing:
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUPS,
            encoding="utf-8",
        )
        file_handler.set_name(FILE_HANDLER)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ExcludeAIFilter())
        root.addHandler(file_handler)

    ai_logger = logging.getLogger(AI_LOGGER_NAME)
    ai_logger.setLevel(settings.LOG_LEVEL.upper())
    if not any(handler.get_name() == AI_FILE_HANDLER for handler in ai_logger.handlers):
        ai_file = RotatingFileHandler(
            log_dir / "ai.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUPS,
            encoding="utf-8",
        )
        ai_file.set_name(AI_FILE_HANDLER)
        ai_file.setFormatter(formatter)
        ai_logger.addHandler(ai_file)
    # Still bubble to root so console shows AI lines; app.log filters them out.
    ai_logger.propagate = True

    # Keep app messages readable; hide database SQL and raw HTTP chatter.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

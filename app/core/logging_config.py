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


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    existing = {handler.get_name() for handler in root.handlers}
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    if CONSOLE_HANDLER not in existing:
        console = logging.StreamHandler()
        console.set_name(CONSOLE_HANDLER)
        console.setFormatter(formatter)
        root.addHandler(console)

    if FILE_HANDLER not in existing:
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUPS,
            encoding="utf-8",
        )
        file_handler.set_name(FILE_HANDLER)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Keep app messages readable; hide database SQL and raw HTTP chatter.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUPS = 5
CONSOLE_HANDLER = "insidehub-console"
FILE_HANDLER = "insidehub-file"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    existing = {handler.get_name() for handler in root.handlers}
    formatter = logging.Formatter(LOG_FORMAT)

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

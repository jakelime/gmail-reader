import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "ggrd"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class CustomLogger:
    def __init__(
        self,
        name: str = __name__,
        level: str = "INFO",
        logfile_dirpath: Path | str | None = None,
        console_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        console_datefmt: str = DATETIME_FMT,
        logfile_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        logfile_datefmt: str = DATETIME_FMT,
        rotating_maxBytes: int = 2_097_152,
        rotating_backupCount: int = 5,
    ):
        self.name = name
        self.level = level
        self.console_fmt = logging.Formatter(fmt=console_fmt, datefmt=console_datefmt)
        self.logfile_fmt = logging.Formatter(fmt=logfile_fmt, datefmt=logfile_datefmt)
        self.rotating_maxBytes = rotating_maxBytes
        self.rotating_backupCount = rotating_backupCount
        match logfile_dirpath:
            case Path():
                pass
            case str():
                logfile_dirpath = Path(logfile_dirpath)
            case _:
                logfile_dirpath = Path(__file__).parent

        self.logfilepath = logfile_dirpath / f"{self.name}.log"
        self.logger = None
        self.getLogger()

    def make_logger(self, logger) -> logging.Logger:
        try:
            logger.setLevel(self.level)
            c_handler = logging.StreamHandler()
            c_handler.setFormatter(self.console_fmt)
            c_handler.setLevel(self.level)
            logger.addHandler(c_handler)
            f_handler = RotatingFileHandler(
                self.logfilepath,
                maxBytes=self.rotating_maxBytes,
                backupCount=self.rotating_backupCount,
            )
            f_handler.setFormatter(self.logfile_fmt)
            f_handler.setLevel(self.level)
            logger.addHandler(f_handler)
            logger.debug(f"logger initialized - {self.logfilepath}")
            return logger
        except Exception as e:
            print(f"logger init failed, {e=}")
            raise e

    def getLogger(self):
        logger = logging.getLogger(self.name)
        if logger.hasHandlers():
            return logger
        return self.make_logger(logger)

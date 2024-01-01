import logging
import shutil
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "ggrd"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class CustomLogger:
    def __init__(
        self,
        name: str = __name__,
        level: str = "INFO",
        console_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        console_datefmt: str = DATETIME_FMT,
        logfile_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        logfile_datefmt: str = DATETIME_FMT,
        rotating_maxBytes: int = 2_097_152,
        rotating_backupCount: int = 5,
        cleanup_on_exit: bool = True,
    ):
        self.tempdir = None
        self.cleanup_on_exit = cleanup_on_exit
        self.name = name
        self.level = level
        self.console_fmt = logging.Formatter(fmt=console_fmt, datefmt=console_datefmt)
        self.logfile_fmt = logging.Formatter(fmt=logfile_fmt, datefmt=logfile_datefmt)
        self.rotating_maxBytes = rotating_maxBytes
        self.rotating_backupCount = rotating_backupCount
        self.logger = None
        self.logger = self.getLogger()

    def make_logger(self, logger) -> logging.Logger:
        try:
            logger.setLevel(self.level)
            c_handler = logging.StreamHandler()
            c_handler.setFormatter(self.console_fmt)
            c_handler.setLevel(self.level)
            logger.addHandler(c_handler)

            self.tempdir = tempfile.mkdtemp(prefix=f"{APP_NAME}-logfiles-")
            self.logfilepath = Path(self.tempdir) / f"{self.name}.log"
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

    def run_cleanup(self):
        if self.logger is not None:
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)
                handler.close()

        if self.cleanup_on_exit and self.tempdir is not None:
            shutil.rmtree(self.tempdir)

from colorlog import StreamHandler, getLogger, ColoredFormatter

import logging


class Logger:
    def __init__(self, name: str):
        handler = StreamHandler()
        handler.setFormatter(
            ColoredFormatter(
                fmt="%(bold_green)s[%(asctime)s]%(reset)s " +
                "%(log_color)s[%(levelname)s/%(name)s]%(reset)s%(thin)s: %(reset)s" +
                "%(log_color)s%(message)s",
                datefmt="%Y-%m-%d | %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "thin",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white"
                }
            )
        )
        self.logger = getLogger(name)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def get_log(self):
        return self.logger

LOG = Logger("CikiECG").get_log()
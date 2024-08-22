from loguru import logger as logging

VALID_LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def configure_logger(file_name, enabled=True, logging_level='INFO'):
    logger = logging.bind(name=__name__)
    return logger.bind(file_name=file_name, enabled=enabled, logging_level=logging_level, trace=True)
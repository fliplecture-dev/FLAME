import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        })


def configure_logging(level: str):
    logger = logging.getLogger("flame")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False

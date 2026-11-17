import logging

from bazaar.app import create_app

logger = logging.getLogger("bazaar")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False

app = create_app()

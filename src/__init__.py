import logging
import os
import sys
from logging.handlers import RotatingFileHandler

log = logging.getLogger()

# The logger will use different files as they surpass 5mb, meaning we will keep the last two if needed.

dirname = os.path.dirname(__file__)
handler = RotatingFileHandler(os.path.join(dirname, "pysolar.log"), mode='a', maxBytes=5*1024*1024,
                              backupCount=2, encoding="utf-8", delay=0)
log.setLevel(logging.INFO)
# handler = logging.FileHandler(filename=os.path.join(dirname, "pysolar.log"), encoding='utf-8', mode='a')
formatter = logging.Formatter("{asctime} - {levelname} - {message}", style="{")

# This ensures that all of our logs are also written to stdout for convenience
stdout_handler = logging.StreamHandler(sys.stdout)
# stderr_handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
# stderr_handler.setFormatter(formatter)
log.addHandler(handler)
log.addHandler(stdout_handler)
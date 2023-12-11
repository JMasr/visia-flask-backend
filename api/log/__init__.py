
import os

from api.log.basic_log_types import BasicLogger

app_logger = BasicLogger(
    log_file=os.path.join(os.getcwd(), "logs", "backend.log")
).get_logger()
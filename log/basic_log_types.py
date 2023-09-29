from datetime import datetime
from enum import Enum

from pydantic import BaseModel

# Variables of possibles origin of logs
log_origin_backend: str = "BACKEND"
log_origin_frontend: str = "FRONTEND"

# Variables of possibles types of logs
log_type_debug: str = "DEBUG"
log_type_error: str = "ERROR"
log_type_info: str = "INFO"
log_type_warning: str = "WARNING"


class LogOrigins(Enum):
    BACKEND: str = log_origin_backend
    FRONTEND: str = log_origin_frontend


class LogTypes(Enum):
    DEBUG: str = log_type_debug
    ERROR: str = log_type_error
    INFO: str = log_type_info
    WARNING: str = log_type_warning


class Log(BaseModel):
    """
    Log class to store log data in MongoDB. Receive logs from the backend or frontend and store them in MongoDB.

    """
    log_origin: LogOrigins
    log_type: LogTypes
    message: str
    timestamp: datetime = datetime.now()

    def model_dump(self, **kwargs) -> dict:
        """
        Return a dict with the model data.
        :return: dict
        """
        dump = {"log_origin": self.log_origin.value,
                "log_type": self.log_type.value,
                "message": self.message}

        return dump

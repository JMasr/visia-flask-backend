from enum import Enum

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

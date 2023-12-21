from pydantic import BaseModel

from api.log import app_logger


class BasicResponse(BaseModel):
    success: bool
    status_code: int
    message: str

    def log_response(self, module: str, action: str):
        """
        Log the response details.
        """
        app_logger.info(
            f"127.0.0.1 - {module} - {action} - Success: {self.success} - "
            f"Message: {self.message} - Status Code: {self.status_code}"
        )


class ListResponse(BasicResponse):
    data: list


class DataResponse(BasicResponse):
    data: dict


class TokenResponse(BasicResponse):
    access_token: str
    refresh_token: str

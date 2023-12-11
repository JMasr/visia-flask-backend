from pydantic import BaseModel


class BasicResponse(BaseModel):
    success: bool
    status_code: int
    message: str


class ListResponse(BasicResponse):
    data: list


class DataResponse(BasicResponse):
    data: dict


class TokenResponse(BasicResponse):
    access_token: str
    refresh_token: str

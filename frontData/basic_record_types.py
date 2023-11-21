from pydantic import BaseModel


class BasicRecordSessionData(BaseModel):
    crd_id: str
    ov: int

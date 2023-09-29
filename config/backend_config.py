from pydantic import BaseModel


class BasicMongoConfig(BaseModel):
    db: str
    username: str
    password: str

    def model_dump(self, **kwargs) -> dict:
        """
        Return a dict with the model data.
        :return: dict
        """
        dump = {"db": self.db,
                "username": self.username,
                "password": self.password}

        return dump

import pickle

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


class BasicSecurityConfig:
    def __init__(self, path_to_secrets: str):
        self.path_to_secrets: str = path_to_secrets
        self.fernet_key: bytes = self._load_encryption_key(self.path_to_secrets + 'fernet_key.pickle')

    def _load_encryption_key(self, path_to) -> bytes:
        """
        Load the encryption key from the config file.
        :return: Encryption key as bytes
        """
        # Load the encryption key using pickle
        with open(path_to, 'rb') as file:
            self.secret_key = pickle.load(file)
        return self.secret_key

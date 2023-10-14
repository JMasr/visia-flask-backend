import os
import pickle

from cryptography.fernet import Fernet
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
        self.fernet_key: bytes = self._load_encryption_key(os.path.join(self.path_to_secrets, "fernet_key.pkl"))

    def _load_encryption_key(self, path_to) -> bytes:
        """
        This method handles the loading of the encryption key.
        If the file exists, it loads a key otherwise it creates a new one.
        :return: Encryption key as bytes
        """
        try:
            # Load the encryption key using pickle
            with open(path_to, 'rb') as file:
                self.secret_key = pickle.load(file)
        except FileNotFoundError:
            # Create a new encryption key
            os.makedirs(os.path.dirname(path_to), exist_ok=True)
            self.secret_key = Fernet.generate_key()
            # Save the encryption key using pickle
            with open(path_to, 'wb') as file:
                pickle.dump(self.secret_key, file)
        return self.secret_key

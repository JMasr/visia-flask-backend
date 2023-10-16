import os
import pickle

from cryptography.fernet import Fernet
from pydantic import BaseModel

from database.basic_mongo import UserDocument, LogDocument
from log.basic_log_types import LogOrigins, log_type_info
from responses.basic_responses import BasicResponse
from security.basic_encription import ObjectEncryptor


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
        self.secret: bytes = self._load_encryption_key(os.path.join(self.path_to_secrets, "secret.pkl"))
        # Encryption Section
        self.encryptor_backend = ObjectEncryptor(key=self.secret)

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

    def add_user(self, username: str, password: str) -> BasicResponse:
        """
        Add a user to the database.
        :param username: Username
        :param password: Password
        :return: True if the user was added successfully, False otherwise
        """
        try:
            # Create a User Document
            encrypted_password = self.encryptor_backend.encrypt_object(password)
            new_user = UserDocument(username=username, password=encrypted_password)
            # Check if the user already exists
            user = UserDocument.objects(username=username)
            if len(user) == 0:
                # Save the user in the database
                new_user.save()

                LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                            message=f"User added: {username}").save()
                response = BasicResponse(success=True, status_code=200, message="User added: successfully")
            else:
                LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                            message=f"User already exists: {username}").save()
                response = BasicResponse(success=True, status_code=400, message="User already exists")
        except ValueError as e:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Invalid Value: {e}").save()
            response = BasicResponse(success=False, status_code=400, message=f'Invalid Value: {e}')
        except Exception as e:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=str(e)).save()
            response = BasicResponse(success=False, status_code=500, message=str(e))

        return response

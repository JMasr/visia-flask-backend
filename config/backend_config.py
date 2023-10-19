import json
import os
import pickle
from time import sleep
from typing import Any

from cryptography.fernet import Fernet
from pydantic import BaseModel
from pymongo import MongoClient

from database.basic_mongo import UserDocument, LogDocument
from log.basic_log_types import LogOrigins, log_type_info
from responses.basic_responses import BasicResponse
from security.basic_encription import ObjectEncryptor
from utils import utils


class BasicMongoConfig(BaseModel):
    credentials: str

    db: str = ""
    username: str = ""
    password: str = ""
    host: str = "localhost"
    port: int = 27017
    is_up: bool = False
    backup_path: str = f"D:\\Visia\\backup_mongo"

    def load_credentials(self):
        """
        Load the credentials from the credentials file.
        """
        credentials_json = self.load_config_from_json(os.path.join(self.credentials, "credentials.json"))
        self.db = credentials_json.get("database", None)
        self.username = credentials_json.get("username", None)
        self.password = credentials_json.get("password", None)

        if self.db is None or self.username is None or self.password is None:
            print("Error loading credentials from file")
            print("Using default credentials")
            self.db = "visia_demo"
            self.username = "rootuser"
            self.password = "rootpass"

    def model_dump(self, **kwargs) -> dict:
        """
        Return a dict with the model data.
        :return: dict
        """
        dump = {"db": self.db,
                "username": self.username,
                "password": self.password}

        return dump

    def mongo_is_up(self) -> bool:
        """
        Check if the MongoDB service is up.
        return: True if the MongoDB service is up, False otherwise.
        """
        try:
            # Check if the MongoDB service is up
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
            # Ping the MongoDB server
            self.is_up = client.admin.command('ping')
            # Close the MongoClient
            client.close()
            print("MongoDB is UP!")
        except Exception or ConnectionError as e:
            print("MongoDB is DOWN!")
            print(f"Error message: {e}")
            self.is_up = False
        return self.is_up

    def wait_for_mongo(self):
        """
        Wait until the MongoDB service is up.
        """
        while not self.mongo_is_up():
            sleep(5)

    @staticmethod
    def save_obj(pickle_name: str, obj: object) -> bool:
        """
        Save an object in a pickle file
        :param pickle_name: path of the pickle file
        :param obj: object to save
        """
        return utils.save_obj(pickle_name, obj)

    @staticmethod
    def load_obj(path_2_pkl: str) -> object:
        """
        Load an object from a pickle file
        :param path_2_pkl: path of the pickle file
        """
        return utils.load_obj(path_2_pkl)

    @staticmethod
    def load_config_from_json(path: str) -> Any | None:
        """
        Load a json file as a dictionary. Useful to load the configuration of the experiments
        :param path: path to the json file
        :return: dictionary with the configuration
        """
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return None
        except Exception or IOError as e:
            print(f"Error loading object: {e}")
            return None

    @staticmethod
    def save_config_as_json(config: dict, path: str) -> bool:
        """
        Save a dictionary as a json file. Useful to save the configuration of the experiments
        :param config: dictionary with the configuration
        :param path: path to save the json file
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                return True
        except Exception or IOError as e:
            print(f"Error saving object: {e}")
            return False


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

import json
import os
import pickle
from time import sleep
from typing import Any

import requests
from cryptography.fernet import Fernet
from pydantic import BaseModel
from pymongo import MongoClient

from api.db.basic_mongo import UserDocument, LogDocument
from api.log.basic_log_types import LogOrigins, log_type_info
from api.responses.basic_responses import BasicResponse
from api.security.basic_encription import ObjectEncryptor
from api.utils import utils


class TestConfig:
    TESTING = True

class BasicServerConfig(BaseModel):
    """
    Class to handle the configuration of the Frontend.
    @:param host: Host of the frontend
    @:param port: Port of the frontend
    @:param is_up: True if the frontend service is up, False otherwise
    """

    host: str = "http://localhost"
    port: int = 8080
    type: str = "Frontend"
    is_up: bool = False

    path_to_config: str

    def load_config(self):
        """
        Load the credentials from the credentials file.
        """
        if not os.path.exists(self.path_to_config):
            print("Error loading credentials from file")
            print("Using default credentials")
        else:
            credentials_json = self.load_config_from_json(self.path_to_config)
            # Create a loop over the class´s attributes
            for attr in self.__dict__:
                if attr in credentials_json:
                    self.__setattr__(attr, credentials_json[attr])
        self.is_up = self.server_is_up()

    def model_dump(self, **kwargs) -> dict:
        """
        Dump the model data as a dictionary.
        :return: A dict with the model data.
        """
        dump: dict = {}
        for attr in self.__dict__:
            dump[attr] = self.__getattribute__(attr)

        return dump

    def server_is_up(self) -> bool:
        """
        Check if the server is up.
        return: True if the server is up, False otherwise.
        """
        try:
            if requests.head(f"{self.host}:{self.port}").status_code == 200:
                self.is_up = True
            else:
                self.is_up = False
        except Exception or ConnectionError as e:
            print(f"Error connecting to the server: {e}")
            self.is_up = False
        return self.is_up

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
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return None
        except Exception or IOError as e:
            print(f"Error loading object: {e}")
            return None


class BasicMongoConfig(BaseModel):
    """
    Class to handle the configuration of the MongoDB database.
    @:param db: Name of the database
    @:param username: Username to access the database
    @:param password: Password to access the database
    @:param host: Host of the database
    @:param port: Port of the database
    @:param is_up: True if the MongoDB service is up, False otherwise
    @:param backup_path: Path to save the backups
    @:param credentials: Path to the credentials file.
    """

    db: str = ""
    username: str = ""
    password: str = ""
    host: str = "http://localhost"
    port: int = 27017
    type: str = "MongoDB"
    is_up: bool = False
    backup_path: str = os.path.join(os.getcwd(), "backups")

    path_to_config: str

    def load_credentials(self):
        """
        Load the credentials from the credentials file.
        """
        self.path_to_config = os.path.join(self.path_to_config, "mongo_config.json")
        if os.path.exists(self.path_to_config):
            # Read the credentials from the credentials file
            credentials_json = self.load_config_from_json(self.path_to_config)

            # Create a loop over the class´s attributes
            for attr in self.__dict__:
                # Check if the attribute is in the credentials file
                if attr in credentials_json:
                    # Set the attribute value
                    self.__setattr__(attr, credentials_json[attr])
        else:
            print("Error loading credentials from file")
            print("Using default credentials")
            self.db = "visia_demo"
            self.username = "rootuser"
            self.password = "rootpass"
            self.host = "localhost"
            self.port = 27017
            self.type = "MongoDB"
            self.backup_path = os.path.join(os.getcwd(), "backups")
        self.is_up = self.server_is_up()

    def model_dump(self, **kwargs) -> dict:
        """
        Dump the model data as a dictionary.
        :return: A dict with the model data.
        """
        dump = {
            "db": self.db,
            "username": self.username,
            "password": self.password,
            "host": self.host,
            "port": self.port,
        }

        return dump

    def server_is_up(self) -> bool:
        """
        Check if the MongoDB service is up.
        return: True if the MongoDB service is up, False otherwise.
        """
        try:
            # Check if the MongoDB service is up
            client = MongoClient(
                f"mongodb://{self.host}:{self.port}/",
                serverSelectionTimeoutMS=2000,
            )
            # Ping the MongoDB server
            self.is_up = client.admin.command("ping")
            # Close the MongoClient
            client.close()
        except Exception or ConnectionError as e:
            print(f"Error connecting to the MongoDB server: {e}")
            self.is_up = False
        return self.is_up

    def wait_for_mongo(self, timeout: int = 5):
        """
        Wait until the MongoDB service is up.
        :param timeout: Timeout in seconds.
        """
        while not self.server_is_up():
            sleep(timeout)

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
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return None
        except Exception or IOError as e:
            print(f"Error loading object: {e}")
            return None


class BasicSecurityConfig:
    """
    Class to handle the security configuration.
    @:param path_to_secrets: Path to the secrets folder
    @:param secret: Encryption key
    @:param encryptor_backend: Encryption backend
    """

    def __init__(self, path_to_secrets: str):
        self.path_to_secrets: str = path_to_secrets
        self.secret: bytes = self._load_encryption_key(
            os.path.join(self.path_to_secrets, "secret.pkl")
        )
        # Encryption Section
        self.encryptor_backend = ObjectEncryptor(key=self.secret)

    def _load_encryption_key(self, path_to) -> bytes:
        """
        This method handles the loading of the encryption key.
        If the file exists, it loads a key otherwise it creates a new one.
        :param path_to: Path to the encryption key
        :return: The encryption key as bytes
        """
        try:
            # Load the encryption key using pickle
            with open(path_to, "rb") as file:
                self.secret_key = pickle.load(file)
        except FileNotFoundError:
            # Create a new encryption key
            os.makedirs(os.path.dirname(path_to), exist_ok=True)
            self.secret_key = Fernet.generate_key()
            # Save the encryption key using pickle
            with open(path_to, "wb") as file:
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

                LogDocument(
                    log_origin=LogOrigins.BACKEND.value,
                    log_type=log_type_info,
                    message=f"User added: {username}",
                ).save()
                response = BasicResponse(
                    success=True,
                    status_code=200,
                    message="User added: successfully",
                )
            else:
                LogDocument(
                    log_origin=LogOrigins.BACKEND.value,
                    log_type=log_type_info,
                    message=f"User already exists: {username}",
                ).save()
                response = BasicResponse(
                    success=True,
                    status_code=400,
                    message="User already exists",
                )
        except ValueError as e:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Invalid Value: {e}",
            ).save()
            response = BasicResponse(
                success=False, status_code=400, message=f"Invalid Value: {e}"
            )
        except Exception as e:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=str(e),
            ).save()
            response = BasicResponse(success=False, status_code=500, message=str(e))

        return response

class BasicCameraConfig(BaseModel):
    path_to_config: str
    controller_path: str = r"C:\Program Files (x86)\digiCamControl"

    iso: int = 100
    aperture: float = 2.8
    exposure_comp: str = "0"
    shutter_speed: str = "1/125"

    auto_focus: bool = True
    compression: str = "RAW"
    white_balance: str = "Auto"

    counter: int = 0
    transfer_mode: str = "Save_to_PC_only"
    image_name: str = "visia_video_[Date yyyy-MM-dd]"
    storage_path: str = os.path.join(os.getcwd(), "uploads")

    type: str = "Camera"

    def load_config(self, logger) -> bool:
        """
        Load the configuration from the JSON file.
        """
        if not os.path.exists(self.path_to_config):
            logger.warning(
                f"Camera: Loading credentials, config file not found - Location: {self.path_to_config}"
            )
            logger.info("Camera: Using default credentials")
        else:
            try:
                credentials_json = self.load_config_from_json(self.path_to_config)
                # Create a loop over the class´s attributes
                for attr in self.__dict__:
                    if attr in credentials_json:
                        self.__setattr__(attr, credentials_json[attr])
                logger.info("Camera: Configuration loaded successfully")
            except Exception as e:
                logger.error(f"Camera: Error loading configuration - {e}")
                return False

        logger.info(f"Camera: Configuration read - {self.model_dump()}")
        return True

    @staticmethod
    def load_config_from_json(path: str) -> Any | None:
        """
        Load a json file as a dictionary. Useful to load the configuration of the experiments
        :param path: path to the json file
        :return: dictionary with the configuration
        """
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return None
        except Exception or IOError as e:
            print(f"Error loading object: {e}")
            return None

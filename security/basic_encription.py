import json

from cryptography.fernet import Fernet
import pickle

from werkzeug.datastructures import FileStorage


class ObjectEncryptor:
    def __init__(self, key: bytes):
        """
        Initialize the ObjectEncryptor with the provided encryption key.
        :param key: Encryption key as bytes
        """
        self.cipher_suite = Fernet(key)

    def encrypt_object(self, data: object) -> bytes:
        """
        Encrypt a Python object.
        :param data: Python object to encrypt
        :return: Encrypted bytes
        """
        serialized_data = pickle.dumps(data)  # Serialize the object to bytes
        cipher_text = self.cipher_suite.encrypt(serialized_data)
        # cipher_text = self.cipher_suite.encrypt(data)
        return cipher_text

    def decrypt_object(self, cipher_text: bytes) -> bytes:
        """
        Decrypt and reconstruct the original Python object.
        :param cipher_text: Encrypted bytes
        :return: Decrypted Python object
        """
        serialized_data = self.cipher_suite.decrypt(cipher_text)
        data = pickle.loads(serialized_data)  # Deserialize the bytes to object
        return data

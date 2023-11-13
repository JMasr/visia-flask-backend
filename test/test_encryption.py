import unittest

from cryptography.fernet import Fernet

from security.basic_encription import ObjectEncryptor


class TestObjectEncryptor(unittest.TestCase):
    def setUp(self):
        # Generate a temporary key for testing
        key = Fernet.generate_key()
        # Create an encryptor
        self.encryptor = ObjectEncryptor(key)

        # Sample data
        self.original_data = {"name": "Alice", "age": 30}

    def test_encryption(self):
        # Encrypt data
        encrypted_data = self.encryptor.encrypt_object(self.original_data)

        # Ensure the encrypted data is not the same as the original data
        self.assertNotEqual(encrypted_data, self.original_data)

    def test_decryption(self):
        # Encrypt data
        encrypted_data = self.encryptor.encrypt_object(self.original_data)
        # Decrypt data
        decrypted_data = self.encryptor.decrypt_object(encrypted_data)

        # Ensure the decrypted data matches the original data
        self.assertEqual(decrypted_data, self.original_data)


if __name__ == "__main__":
    unittest.main()

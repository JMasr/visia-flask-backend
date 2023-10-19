import os
import subprocess

from pydantic import BaseModel
from utils.utils import get_now_standard


class BackUp():
    """
    Class to perform backups of the MongoDB database.
    """

    def __init__(self, mongo_config: BaseModel):
        self.mongo_config = mongo_config

    def make(self) -> bool:
        """
        Make a backup of the database and save it in the backup path.
        :return: True if the backup was successful, False otherwise.
        """
        try:
            os.makedirs(os.path.dirname(self.mongo_config.backup_path), exist_ok=True)
            # Define the command to run mongodump
            cmd = [
                f"{os.path.join(os.getcwd(), 'utils', 'mongodump.exe')}",
                '--db', f'{self.mongo_config.db}',
                '--out', f'{os.path.join(self.mongo_config.backup_path, get_now_standard())}',
                '--username', f'{self.mongo_config.username}',
                '--password', f'{self.mongo_config.password}',
                '--authenticationDatabase', 'admin',
                '--host', f'{self.mongo_config.host}',
                '--port', f'{self.mongo_config.port}'
            ]

            # Run the command
            subprocess.run(cmd)

            # Save the backup file
            return True
        except Exception as e:
            print(f"Error making backup: {e}")
            return False

    def restore(self, backup_date: str) -> bool:
        """
        Restore the database from a backup file on the backup path.
        """
        try:
            # Define the command to run mongorestore
            cmd = [
                f"{os.path.join(os.getcwd(), 'utils', 'mongorestore.exe')}",
                '--db', f'visia_backup_{backup_date}',
                f'{os.path.join(self.mongo_config.backup_path, backup_date, self.mongo_config.db)}',
                '--username', f'{self.mongo_config.username}',
                '--password', f'{self.mongo_config.password}',
                '--authenticationDatabase', 'admin',
                '--host', f'{self.mongo_config.host}',
                '--port', f'{self.mongo_config.port}'
            ]

            # Run the command
            subprocess.run(cmd)

            return True
        except FileExistsError or FileNotFoundError as e:
            print(f"Error restoring backup: {e}")
            return False
        except ConnectionError or Exception as e:
            print(f"Error: {e}")
            return False

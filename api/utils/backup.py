import os
import platform
import subprocess
from datetime import datetime

from pydantic import BaseModel

from api.responses.basic_responses import BasicResponse
from api.utils.utils import get_now_standard


class BackUp:
    """
    Class to perform backups of the MongoDB database.
    """

    def __init__(self, mongo_config: BaseModel):
        self.backup_count: int = 5
        self.backup_by_day: int = 2
        self.mongo_config: BaseModel = mongo_config

        self.actions_by_backup_status = {
            501: self.delete_old_backups,
            502: self.delete_old_backups_per_day,
        }

    def check_backup_policies(self) -> BasicResponse:
        """
        Check the backup policies
        @return: A BasicResponse with the result of the operation. True if they are satisfy, False otherwise. The status
        code will be 200 if the policies are satisfied, 501 if there are too many backup files and 502 if there are to
        many backup files per day.
        """
        try:
            backup_files = os.listdir(self.mongo_config.backup_path)
            backup_amount = len(backup_files)

            if (
                    backup_amount == 0
                    or backup_amount < self.backup_by_day
                    or backup_amount < self.backup_count
            ):
                response = BasicResponse(
                    success=True,
                    message="Backup policies are satisfied",
                    status_code=200,
                )
            elif backup_amount > self.backup_count:
                response = BasicResponse(
                    success=False, message="Too many backup files", status_code=501
                )
            elif backup_amount > self.backup_by_day:
                response = BasicResponse(
                    success=False,
                    message="Too many backup files per day",
                    status_code=502,
                )
            else:
                response = BasicResponse(
                    success=True,
                    message="Backup policies are satisfied",
                    status_code=200,
                )
        except (IOError, OSError) as e:
            response = BasicResponse(
                success=False,
                message=f"Error checking backup policies: {e}",
                status_code=500,
            )

        response.log_response("Backup", "Check Backup Policies")
        return response

    def resolve_backup_policies(self, backup_status_code: int) -> BasicResponse:
        """
        Resolve the backup policies using the policies status
        @param backup_status_code: The status code of the backup policies
        @return: A BasicResponse with the result of the operation. True if they are satisfy, False otherwise.
        """
        # Take the corresponding action
        try:
            action = self.actions_by_backup_status.get(backup_status_code, None)
            if action:
                response = action()
            else:
                response = BasicResponse(
                    success=False,
                    message=f"Invalid backup status code: {backup_status_code}",
                    status_code=500,
                )
        except Exception as e:
            response = BasicResponse(
                success=False,
                message=f"Error resolving backup policies: {e}",
                status_code=500,
            )

        response.log_response("Backup", "Resolve Backup Policies")
        return response

    def delete_old_backups(self) -> BasicResponse:
        """
        Delete old backups based on the overall backup count.
        @return: A BasicResponse with the result of the operation.True if the old backups were deleted, False otherwise.
        """
        try:
            backup_files = os.listdir(self.mongo_config.backup_path)
            backup_files.sort()

            while len(backup_files) > self.backup_count:
                file_to_delete = os.path.join(
                    self.mongo_config.backup_path, backup_files.pop(0)
                )
                os.rmdir(file_to_delete)

            response = BasicResponse(
                success=True, message="Old backups deleted", status_code=200
            )
        except Exception as e:
            response = BasicResponse(
                success=False,
                message=f"Error deleting old backups: {e}",
                status_code=500,
            )

        response.log_response("Backup", "Delete Old Backups")
        return response

    def delete_old_backups_per_day(self) -> BasicResponse:
        """
        Delete old backups based on the daily backup count.
        @return: A BasicResponse with the result of the operation.
        """
        try:
            backup_files = os.listdir(self.mongo_config.backup_path)
            backup_files.sort(key=os.path.getctime)

            today = datetime.now().date()
            backups_today = [
                f
                for f in backup_files
                if datetime.fromtimestamp(os.path.getctime(f)).date() == today
            ]

            while len(backups_today) > self.backup_by_day:
                file_to_delete = os.path.join(
                    self.mongo_config.backup_path, backups_today.pop(0)
                )
                os.remove(file_to_delete)

            response = BasicResponse(
                success=True, message="Old backups deleted", status_code=200
            )
        except Exception as e:
            response = BasicResponse(
                success=False,
                message=f"Error deleting old backups per day: {e}",
                status_code=500,
            )

        response.log_response("Backup", "Delete Old Backups Per Day")
        return response

    def mongo_dump(self) -> bool:
        """
        Make a backup of the MongoDB database.
        @return: True if the backup was made, False otherwise.
        """
        try:
            # Create the backup path if it doesn't exist
            os.makedirs(os.path.dirname(self.mongo_config.backup_path), exist_ok=True)

            # Check the backup policies
            policies_status = self.check_backup_policies()
            if policies_status.status_code != 200:
                self.resolve_backup_policies(policies_status.status_code)

            # Make the backup
            if platform.system() == "Windows":
                # Define the command to run mongodump for Windows
                cmd = [
                    os.path.join(os.getcwd(), "utils", "mongodump.exe"),
                    "--db",
                    self.mongo_config.db,
                    "--out",
                    os.path.join(self.mongo_config.backup_path, get_now_standard()),
                    "--username",
                    self.mongo_config.username,
                    "--password",
                    self.mongo_config.password,
                    "--authenticationDatabase",
                    "admin",
                    "--host",
                    self.mongo_config.host,
                    "--port",
                    str(self.mongo_config.port),
                ]
            else:  # Assume it's Linux
                # Define the command to run mongodump for Linux
                cmd = [
                    os.path.join(os.getcwd(), "utils", "mongodump"),
                    "--db",
                    self.mongo_config.db,
                    "--out",
                    os.path.join(self.mongo_config.backup_path, get_now_standard()),
                    "--username",
                    self.mongo_config.username,
                    "--password",
                    self.mongo_config.password,
                    "--authenticationDatabase",
                    "admin",
                    "--host",
                    self.mongo_config.host,
                    "--port",
                    str(self.mongo_config.port),
                ]

            # Run the command
            subprocess.run(cmd)
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
                "--db",
                f"visia_backup_{backup_date}",
                f"{os.path.join(self.mongo_config.backup_path, backup_date, self.mongo_config.db)}",
                "--username",
                f"{self.mongo_config.username}",
                "--password",
                f"{self.mongo_config.password}",
                "--authenticationDatabase",
                "admin",
                "--host",
                f"{self.mongo_config.host}",
                "--port",
                f"{self.mongo_config.port}",
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

import os
import time
from typing import List, Optional

import cv2
from pydantic import BaseModel

from api.log import app_logger


def check_for_new_files(
    path_folder: str, previous_files: List[str] = None, timer_seconds: int = 10
) -> bool:
    """
    Check if there is any new file on a specific folder by a specific time in seconds
    @param: path_folder: Path to the folder to be checked
    @param: timer_seconds: Max seconds of the
    @param: previous_files: A list with the files already in the folder
    @return: True if there is a new file before the timer reaches 0, otherwise False
    """

    if previous_files is None:
        previous_files = []

    if not (path_folder and os.path.exists(path_folder) and os.path.isdir(path_folder)):
        app_logger.warning("127.0.0.1 - util.check_for_new_files - Invalid path folder")
        return False

    start_time = time.time()
    while time.time() - start_time < timer_seconds:
        # Get the current list of files in the folder
        current_files = os.listdir(path_folder)

        # Check if there are new files
        new_files = set(current_files) - set(previous_files)
        if new_files:
            app_logger.info(
                f"127.0.0.1 - util.check_for_new_files - New files detected: {new_files}"
            )
            return True

        # Check if the timer exceeds the limit
        if time.time() - start_time >= timer_seconds:
            app_logger.info(
                "127.0.0.1 - util.check_for_new_files - Timer limit reached"
            )
            break

        # Wait for a short interval before checking again
        time.sleep(10)

    return False


def get_newest_file_in_folder(path_folder: str) -> Optional[str]:
    """
    Get the last file created in a specific folder.
    @param: path_folder: Path to the folder to be checked
    @return: The last created file in the folder or None if the folder is empty
    """
    if not (path_folder and os.path.exists(path_folder) and os.path.isdir(path_folder)):
        app_logger.warning(
            "127.0.0.1 - util.get_last_created_file - Invalid path folder"
        )
        return None

    try:
        sorted_files = files_in_folder_sorted_by_time(path_folder)

        # Return the name of the last created file
        return sorted_files[0][0] if sorted_files else None
    except Exception as e:
        app_logger.error(f"127.0.0.1 - util.get_last_created_file - Error: {e}")
        return None


def get_older_file_in_folder(path_folder: str) -> Optional[str]:
    """
    Get the older file created in a specific folder.
    @param: path_folder: Path to the folder to be checked
    @return: The older file in the folder or None if the folder is empty
    """
    if not (path_folder and os.path.exists(path_folder) and os.path.isdir(path_folder)):
        app_logger.warning(
            "127.0.0.1 - util.get_last_created_file - Invalid path folder"
        )
        return None

    try:
        sorted_files = files_in_folder_sorted_by_time(path_folder)

        # Return the name of the last created file
        return sorted_files[-1][-1] if sorted_files else None
    except Exception as e:
        app_logger.error(f"127.0.0.1 - util.get_last_created_file - Error: {e}")
        return None


def files_in_folder_sorted_by_time(path_folder: str) -> list:
    """
    List and sort by creation time all the files in a directory.
    @param: path_folder: Path to the directory
    @return: A list with all the files sorted by creation time.
    """
    # Get a list of files in the folder with their creation times
    files_with_times = [
        (file, os.path.getctime(os.path.join(path_folder, file)))
        for file in os.listdir(path_folder)
    ]
    # Sort files by creation time (newest first)
    sorted_files = sorted(files_with_times, key=lambda x: x[1], reverse=True)
    return sorted_files


def get_video_properties(video_path: str) -> dict:
    """
    Get the properties of a video file.
    @param video_path: Path to the video file
    """
    video_properties = {}
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print("Error: Could not open video file.")
            return video_properties

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        # Release the video file
        cap.release()

        # Convert codec to four-character code
        codec_fourcc = (
            chr(codec & 0xFF)
            + chr((codec >> 8) & 0xFF)
            + chr((codec >> 16) & 0xFF)
            + chr((codec >> 24) & 0xFF)
        )

        # Store video properties in a dictionary
        video_properties = {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "codec_fourcc": codec_fourcc,
        }

        # Log video properties
        app_logger.info(
            "Video - Properties - OK -"
            f" FPS: {fps} "
            f" Frame Count: {frame_count}"
            f" Resolution: {width}x{height}"
            f" Codec: {codec_fourcc}"
        )
        return video_properties
    except Exception as e:
        app_logger.error(
            f"Video - Properties - Error - Fails to get video properties: {e}"
        )
        return video_properties


class BasicFileConfig(BaseModel):
    uploads_path: str = os.path.join(os.getcwd(), "uploads")
    backups_path: str = os.path.join(os.getcwd(), "backups")
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)

    upload_files: list = os.listdir(uploads_path)

    def update_upload_files(self):
        """
        Update the list of files in the uploads folder.
        """
        self.upload_files = os.listdir(self.uploads_path)

    def get_newest_file(self):
        """
        Get the path to last created file in the upload folder.
        """
        return os.path.join(
            self.uploads_path, get_newest_file_in_folder(self.uploads_path)
        )

    def exists(self, file_name: str = None) -> bool:
        """
        Check if a file exists in the upload folder. If the file_name is None, it checks if the uploads folder is empty.
        """
        if file_name is None:
            file_name = self.uploads_path
        else:
            file_name = os.path.join(self.uploads_path, file_name)
        return os.path.exists(file_name)

    def check_for_new_files(self, waiting_time: int = 60 * 15):
        """
        Check if there is any new file in the upload folder during a specific time.
        @param: waiting_time: Max seconds of the waiting time
        @return: True if there is a new file before the timer reaches 0, otherwise False
        """
        are_new_files = check_for_new_files(
            self.uploads_path, timer_seconds=waiting_time
        )
        self.update_upload_files()
        return are_new_files

    def delete_all_files(self) -> bool:
        """
        Delete all files in the uploads folder.
        """
        try:
            for file in os.listdir(self.uploads_path):
                os.remove(os.path.join(self.uploads_path, file))
            self.update_upload_files()
            return True
        except Exception as e:
            app_logger.error(f"Error deleting files: {e}")
            return False

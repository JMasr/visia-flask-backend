import os
import time
from typing import List, Optional

from config.backend_config import logger


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
        logger.warning("127.0.0.1 - util.check_for_new_files - Invalid path folder")
        return False

    start_time = time.time()
    while time.time() - start_time < timer_seconds:
        # Get the current list of files in the folder
        current_files = os.listdir(path_folder)

        # Check if there are new files
        new_files = set(current_files) - set(previous_files)
        if new_files:
            logger.info(
                f"127.0.0.1 - util.check_for_new_files - New files detected: {new_files}"
            )
            return True

        # Check if the timer exceeds the limit
        if time.time() - start_time >= timer_seconds:
            logger.info("127.0.0.1 - util.check_for_new_files - Timer limit reached")
            break

        # Wait for a short interval before checking again
        time.sleep(1)

    return False


def get_last_created_file(path_folder: str) -> Optional[str]:
    """
    Get the last file created in a specific folder.
    @param: path_folder: Path to the folder to be checked
    @return: The last created file in the folder or None if the folder is empty
    """
    if not (path_folder and os.path.exists(path_folder) and os.path.isdir(path_folder)):
        logger.warning("127.0.0.1 - util.get_last_created_file - Invalid path folder")
        return None

    try:
        # Get a list of files in the folder with their creation times
        files_with_times = [
            (file, os.path.getctime(os.path.join(path_folder, file)))
            for file in os.listdir(path_folder)
        ]

        # Sort files by creation time (newest first)
        sorted_files = sorted(files_with_times, key=lambda x: x[1], reverse=True)

        # Return the name of the last created file
        return sorted_files[0][0] if sorted_files else None
    except Exception as e:
        logger.error(f"127.0.0.1 - util.get_last_created_file - Error: {e}")
        return None
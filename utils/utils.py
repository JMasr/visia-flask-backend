import os
import pickle
from datetime import datetime

from pydantic import BaseModel

from database.basic_mongo import VideoDocument, LogDocument, UserDocument


def get_now_standard() -> str:
    """
    Get the current date and time in a standard format.
    :return: A string with the current date and time in the standard format.
    """
    return datetime.now().strftime("%d-%m-%y_%H-%M-%S")


def save_obj(pickle_name: str, obj: object) -> bool:
    """
    Save an object in a pickle file
    :param pickle_name: path of the pickle file
    :param obj: object to save
    """
    try:
        os.makedirs(os.path.dirname(pickle_name), exist_ok=True)
        with open(pickle_name, 'wb') as handle:
            pickle.dump(obj, handle, 0)
        return True
    except Exception or IOError as e:
        print(f"Error saving object: {e}")
        return False


def load_obj(path_2_pkl: str) -> object:
    """
    Load an object from a pickle file
    :param path_2_pkl: path of the pickle file
    """
    try:
        if os.path.exists(path_2_pkl):
            with open(path_2_pkl, 'rb') as pkl_file:
                return pickle.load(pkl_file)
        else:
            return None
    except Exception or IOError as e:
        print(f"Error loading object: {e}")
        return None



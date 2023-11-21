import os
import json
import pickle
from datetime import datetime


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
        with open(pickle_name, "wb") as handle:
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
            with open(path_2_pkl, "rb") as pkl_file:
                return pickle.load(pkl_file)
        else:
            return None
    except Exception or IOError as e:
        print(f"Error loading object: {e}")
        return None


def save_config_as_json(config: dict, path: str) -> bool:
    """
    Save a dictionary as a json file. Useful to save the configuration of the experiments
    :param config: dictionary with the configuration
    :param path: path to save the json file
    :return: True if the file was saved successfully, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            return True
    except Exception or IOError as e:
        print(f"Error saving object: {e}")
        return False

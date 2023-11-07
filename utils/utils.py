import os
import pickle
from datetime import datetime

import cv2


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


def get_video_properties(video_path):
    # Open the video file
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    codec = int(cap.get(cv2.CAP_PROP_FOURCC))

    # Convert codec to four-character code
    codec_fourcc = chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr((codec >> 24) & 0xFF)

    # Print video properties
    print(f"FPS: {fps}")
    print(f"Frame Count: {frame_count}")
    print(f"Resolution: {width}x{height}")
    print(f"Codec: {codec_fourcc}")

    # Release the video file
    cap.release()


if __name__ == "__main__":
    video_path = r"C:\Users\jmram\Documents\GitHub\visia\visia-flask-backend\uploads\test\digcam.MP4"
    if os.path.exists(video_path):
        get_video_properties(video_path)
    else:
        print("Error: Video file does not exist.")

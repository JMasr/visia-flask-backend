from datetime import datetime


def get_now_standard() -> str:
    """
    Get the current date and time in a standard format.
    :return: A string with the current date and time in the standard format.
    """
    return datetime.now().strftime("%d-%m-%y_%H-%M-%S")

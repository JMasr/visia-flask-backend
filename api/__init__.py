from flask import Flask

from api.api import APP


def create_app(deploy: bool = True) -> Flask:
    """
    Create a Flask api with the specified configuration.
    :param deploy: The configuration to use for the Flask api. If True, the TestConfig will be used.
    """

    return APP(deploy=deploy).create_app()

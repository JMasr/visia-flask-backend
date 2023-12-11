import os

from flask import Blueprint, request, send_from_directory
from flask_cors import cross_origin
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from api.config.backend_config import BasicSecurityConfig, BasicMongoConfig
from api.log import app_logger
from api.responses.basic_responses import BasicResponse
from api.utils.files import BasicFileConfig

bp_general = Blueprint('bp_general', __name__)

# Data Handler Section
file_config = BasicFileConfig()
file_config.update_upload_files()

# Set the secret key to enable JWT authentication
security_config = BasicSecurityConfig(
        path_to_secrets=os.path.join(os.getcwd(), "secrets")
    )

# Configure MongoDB
mongo_config = BasicMongoConfig(path_to_config=os.path.join(os.getcwd(), "secrets"))
mongo_config.load_credentials()


# Endpoints Section
@bp_general.route("/")
@cross_origin()
def index():
    """
    A simple endpoint with a welcome message from the Backend.
    :return: A welcome message from the Backend.
    """
    app_logger.info(f'{request.remote_addr} - "GET /" -')
    return "Welcome to the VISIA-BackEnd v2.0!"

@bp_general.route("/favicon.ico")
def favicon():
    """
    A simple endpoint to get the favicon.ico file.
    :return: A favicon.ico file.
    """
    app_logger.info(f'{request.remote_addr} - "GET /favicon.ico" -')
    return send_from_directory(
        os.path.join(os.getcwd(), "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )

@bp_general.route("/poll")
@cross_origin()
def poll():
    """
    A simple endpoint to test the connection with the Backend
    :return: A BasicResponse with the status of the Backend
    """
    app_logger.info(f'{request.remote_addr} - "GET /poll" -')
    try:
        # Initialize a MongoClient
        client = MongoClient(
            f"mongodb://{mongo_config.host}:{mongo_config.port}/",
            serverSelectionTimeoutMS=2000,
        )
        # Ping the MongoDB server
        is_up = client.admin.command("ping")
        # Close the MongoClient
        client.close()

        if is_up.get("ok") == 1.0:
            response = BasicResponse(
                success=True,
                message="Flask and MongoDB are UP!",
                status_code=200,
            )
        else:
            response = BasicResponse(
                success=False,
                message="Flask is UP! and MongoDB is UP but not WORKING!",
                status_code=400,
            )
    except Exception or ConnectionError or TimeoutError:
        response = BasicResponse(
            success=False,
            message="Flask is UP! but MongoDB is DOWN!",
            status_code=503,
        )

    return response.model_dump_json()

@bp_general.errorhandler(404)
def resource_not_found():
    """
    An error-handler to ensure that 404 errors are returned as JSON.
    :return: A BasicResponse representing a 404 error.
    """
    app_logger.error(f'{request.remote_addr} - "GET /{request.url}" - ERROR: Resource not found')
    response = BasicResponse(
        success=False,
        status_code=404,
        message=f"Resource not found: {request.url}",
    )
    return response.model_dump()

@bp_general.errorhandler(DuplicateKeyError)
def resource_not_found(e):
    """
    An error-handler to ensure that MongoDB duplicate key errors are returned as JSON.
    :return: A BasicResponse representing a duplicate key error from MongoDB.
    """
    app_logger.error(f'{request.remote_addr} - "GET /{request.url}" - ERROR: Duplicate key error: {str(e)}')
    response = BasicResponse(
        success=False,
        status_code=500,
        message=f"Duplicate key error: {str(e)}",
    )
    return response.model_dump_json()

from flask import Blueprint, request
from flask_cors import cross_origin

from api.db.basic_mongo import LogActionsMongoDB
from api.log import app_logger
from api.log.basic_log_types import LogOrigins
from api.responses.basic_responses import BasicResponse

bp_logs = Blueprint("bp_logs", __name__)


@bp_logs.route("/log/addLogFrontEnd", methods=["POST"])
@cross_origin()
def upload_log_frontend() -> str:
    """
    Endpoint to log data from the FrontEnd
    :return: A JSON object with a message and a status code.
    """
    app_logger.info(f'{request.remote_addr} - "POST /log/addLogFrontEnd" -')

    try:
        # Get data from request body
        log_type = request.json.get("log_type")
        message = request.json.get("message")

        app_logger.info(
            f'{request.remote_addr} - "POST /log/addLogFrontEnd" - OK: {message}'
        )
        response = LogActionsMongoDB(
            log_origin=LogOrigins.FRONTEND.value,
            log_type=log_type,
            message=message,
        ).insert_log()

    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "POST /log/addLogFrontEnd" - ERROR: {e}'
        )
        response = BasicResponse(
            success=False, status_code=400, message=f"Bad request: {e}"
        )

    return response.model_dump_json()


@bp_logs.route("/log/addLogBackEnd", methods=["POST"])
def upload_log_backend() -> str:
    """
    Endpoint to log data from the BackEnd
    :return: A JSON object with a message and a status code.
    """
    app_logger.info(f'{request.remote_addr} - "POST /log/addLogBackEnd" -')

    try:
        # Get data from request body
        log_type = request.json.get("log_type")
        message = request.json.get("message")

        app_logger.info(
            f'{request.remote_addr} - "POST /log/addLogBackEnd" - OK: {message}'
        )
        response = LogActionsMongoDB(
            log_origin=LogOrigins.BACKEND.value, log_type=log_type, message=message
        ).insert_log()
    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "POST /log/addLogBackEnd" - ERROR: {e}'
        )
        response = BasicResponse(
            success=False, status_code=400, message=f"Bad request: {e}"
        )

    return response.model_dump_json()


# Endpoint to retrieve logs by type
@bp_logs.route("/log/getLogsBy", methods=["GET"])
@cross_origin()
def get_logs_by() -> str:
    """
    Endpoint to retrieve logs from the MongoDB database based on specified filters.
    We use a dictionary containing filter criteria, if one of the is empty we ignore and use the others, e.g.,
     {'log_type': 'DEBUG', 'log_origin': 'BACKEND'., 'id': '096asdf'}
    :return: A JSON object with a list of logs or a message and a status code.
    """
    app_logger.info(f'{request.remote_addr} - "GET /log/getLogsBy" -')

    try:
        # Get data from request
        data = request.args
        # Get data from request body
        query = {key: value for key, value in data.items() if value != ""}
        # Create a Log Action
        response = LogActionsMongoDB.get_logs_by_type(query)
        app_logger.info(
            f'{request.remote_addr} - "GET /log/getLogsBy" - OK: {response.message}'
        )
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
        app_logger.error(
            f'{request.remote_addr} - "GET /log/getLogsBy" - ERROR: {str(e)}'
        )

    return response.model_dump_json()

import os

from flask import Blueprint, request, redirect
from flask_cors import cross_origin
from pydantic import BaseModel

from api.config.backend_config import BasicServerConfig
from api.db.basic_mongo import LogDocument
from api.log import app_logger
from api.log.basic_log_types import LogOrigins, log_type_info, log_type_error
from api.responses.basic_responses import DataResponse

# Set the blueprint
bp_render = Blueprint("bp_render", __name__)

# Configure FrontEnd
react_app = BasicServerConfig(
    path_to_config=os.path.join(os.getcwd(), "secrets", "frontend_config.json")
)
react_app.load_config()


class BasicRecordSessionData(BaseModel):
    crd_id: str
    ov: int


# Render section
record_data = BasicRecordSessionData(crd_id="001-T-CRD", ov=1)


# Render functions for the frontend
@bp_render.route("/render/getRecordData")
@cross_origin()
def get_record_session_data():
    """
    Endpoint to get the data for a Record-Session.
    :return: A DataResponse with the data for a Record-Session.
    """
    app_logger.info(f'{request.remote_addr} - "GET /render/getRecordData" -')
    try:
        response = DataResponse(
            success=True,
            status_code=200,
            message="Data for Record-Session is ready",
            data=record_data.model_dump(),
        )
        app_logger.info(
            f'{request.remote_addr} - "GET /render/getRecordData" - OK: {response.message}'
        )

    except ValueError as e:
        response = DataResponse(
            success=False,
            status_code=400,
            message=f"Value Error: {e}",
            data={},
        )
        app_logger.error(
            f'{request.remote_addr} - "GET /render/getRecordData" - ERROR: {response.message}'
        )

    except Exception as e:
        response = DataResponse(
            success=False, status_code=400, message=f"Error: {e}", data={}
        )
        app_logger.error(
            f'{request.remote_addr} - "GET /render/getRecordData" - ERROR: {response.message}'
        )

    return response.model_dump()


@bp_render.route("/video", methods=["GET"])
@cross_origin()
def get_render_video():
    """
    Endpoint to render a video file from a get request.
    :return: a redirection to the VideoRecording Frontend service.
    """
    app_logger.info(f'{request.remote_addr} - "GET /video" -')
    try:        # Get data from request
        record_data.crd_id = request.args.get("crd", "UNK")
        record_data.ov = request.args.get("ov", "UNK")
        # Add a log
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_info,
            message=f"Video requested: {record_data.crd_id}--{record_data.ov}",
        ).save()
        app_logger.info(
            f'{request.remote_addr} - "GET /video" - OK: Video requested: {record_data.crd_id}--{record_data.ov}'
        )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        app_logger.error(f'{request.remote_addr} - "GET /video" - ERROR: {str(e)}')

    return redirect(f"{react_app.host}:{react_app.port}/")

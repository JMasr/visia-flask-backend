import base64
import os
import time

import cv2
from flask import Blueprint, request
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required

from api.config.backend_config import BasicSecurityConfig, BasicMongoConfig
from api.db.basic_mongo import VideoActionsMongoDB, LogDocument
from api.hardware.cam import Camera
from api.log import app_logger
from api.log.basic_log_types import (
    LogOrigins,
    log_type_info,
    log_type_error,
    log_type_warning,
)
from api.responses.basic_responses import BasicResponse, DataResponse, ListResponse
from api.utils.backup import BackUp
from api.utils.files import BasicFileConfig, check_for_new_files, get_video_properties
from api.utils.utils import get_now_standard

bp_video = Blueprint("bp_video", __name__)

# Data Handler Section
file_config = BasicFileConfig()
file_config.update_upload_files()

# Set the secret key to enable JWT authentication
security_config = BasicSecurityConfig(
    path_to_secrets=os.path.join(os.getcwd(), "secrets")
)

# Create a backup
mongo_config = BasicMongoConfig(path_to_config=os.path.join(os.getcwd(), "secrets"))
mongo_config.load_credentials()
backup = BackUp(mongo_config)

# Configure the camera if a config file is present
camera = Camera()


@bp_video.route("/video/digicam/startVideo", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_start_video() -> str:
    """
    Endpoint to start recording a video file using DigicamControl.
    @return: A BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /video/digicam/startVideo"')

    if not camera.is_camera():
        app_logger.error(f'{request.remote_addr} - "GET /video/digicam/startVideo" - ERROR - Isn\'t a camera connected')
        return BasicResponse(
            success=False,
            status_code=400,
            message="Camera not connected",
        ).model_dump_json()

    if not camera.is_running():
        app_logger.warning(
            f'{request.remote_addr} - "GET /video/digicam/startVideo" - digiCam isn\'t running'
        )
        camera.run_digicam()

    try:
        camera_response = camera.start_recording()
        if camera_response.success:
            app_logger.info(
                f'{request.remote_addr} - "GET /video/digicam/startVideo" - 200 - digiCam start the recording'
            )
            return BasicResponse(
                success=True,
                status_code=200,
                message="Video recording started",
            ).model_dump_json()
        else:
            app_logger.error(
                f'{request.remote_addr} - "GET /video/digicam/startVideo" - 500 - digiCam failed to start recording'
            )
            return BasicResponse(
                success=False,
                status_code=400,
                message="Video recording not started",
            ).model_dump_json()

    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "GET /video/digicam/startVideo" - 500 - Error: {e}'
        )

        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@bp_video.route("/video/digicam/stopVideo", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_stop_video() -> str:
    """
    Endpoint to stop recording a video file using DigicamControl.
    @return: A BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /video/digicam/stopVideo"')

    try:
        # Save the number of files before recording
        file_config.update_upload_files()

        # Stop the recording
        recording_r: BasicResponse = camera.stop_recording()
        # Log the response
        if recording_r.success:
            app_logger.info(
                f"{request.remote_addr} - POST /video/digicam/stopVideo - 200"
            )
        else:
            app_logger.error(
                f"{request.remote_addr} -POST /video/digicam/stopVideo - 500 - Error: {recording_r.message}"
            )

        return recording_r.model_dump_json()
    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "POST /video/digicam/stopVideo" - 500 - Error: {e}'
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@bp_video.route("/video/digicam/preview", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_preview():
    """
    Use digicam to record a video and take one frame as a visualization of the camera
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /video/digicam/preview"')

    if not camera.is_camera():
        app_logger.error(f'{request.remote_addr} - "GET /video/digicam/preview" - ERROR - Isn\'t a camera connected')
        return BasicResponse(
            success=False,
            status_code=400,
            message="Camera not connected",
        ).model_dump_json()

    try:
        if not camera.is_running():
            app_logger.warning(
                f'{request.remote_addr} - "GET /video/digicam/preview" - digicam isnt running'
            )
            camera.run_digicam()

        camera_response = camera.start_recording()
        if camera_response.success:
            app_logger.info(
                f'{request.remote_addr} - "GET /video/digicam/preview" - OK - digiCam start the recording'
            )

            file_config.update_upload_files()
            time.sleep(1.5)
            camera_response = camera.stop_recording()

            if camera_response.success:
                app_logger.info(
                    f'{request.remote_addr} - "GET /video/digicam/preview" - OK - digiCam stop the recording'
                )

                # Way for the video transferring
                if check_for_new_files(
                        path_folder=file_config.uploads_path,
                        previous_files=file_config.upload_files,
                        timer_seconds=120,
                ):
                    video_path: str = file_config.get_newest_file()
                    response = send_video_frame_as_json(video_path)
                    file_config.delete_all_files()

                    app_logger.info(
                        f'{request.remote_addr} - "GET /video/digicam/preview" - OK - Video recorded and upload'
                    )

                    return response.model_dump_json()

        app_logger.error(
            f'{request.remote_addr} - "GET /video/digicam/preview" - 501 - Video Recorded but not uploaded'
        )
        return BasicResponse(
            success=False, status_code=501, message=camera_response.message
        ).model_dump_json()
    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "GET /video/digicam/preview" - Error {e}'
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@bp_video.route("/file/checkFile", methods=["GET"])
# @jwt_required()
@cross_origin()
def check_new_file():
    """
    Endpoint to check if a new file is present in the upload folder.
    :return: a BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /files/checkFiles"')

    try:
        # Way for the file transferring/storage/etc
        if not file_config.check_for_new_files():
            app_logger.warning(
                f"{request.remote_addr} - POST /files/checkFiles - "
                f"WARNING - Nothing found on: {file_config.upload_files}"
            )

            return BasicResponse(
                success=False, status_code=500, message="No new files found"
            ).model_dump_json()

        app_logger.info(
            f"{request.remote_addr} - POST /files/checkFiles - OK - New file found: {file_config.get_newest_file()}"
        )

        return BasicResponse(
            success=True,
            status_code=200,
            message=f"New file found: {file_config.get_newest_file()}",
        ).model_dump_json()

    except Exception as e:
        # Add a log
        app_logger.error(
            f"{request.remote_addr} - POST /files/checkFiles - 500 - Error: {e}"
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@bp_video.route("/file/uploadLastCreated", methods=["POST"])
# @jwt_required()
@cross_origin()
def save_new_file(video_format: str = "mp4") -> str:
    """
    Endpoint to save the last created file in the upload folder.
    :param video_format: a string representing the video format.
    :return: a BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /files/uploadLastCreated"')
    # Check request body
    try:
        crd_id: str = request.json.get("crdId", "UNK")
        if crd_id == "UNK":
            app_logger.warning(
                f"{request.remote_addr} - POST /files/uploadLastCreated - CRD_ID missed!!"
            )
        else:
            app_logger.info(
                f"{request.remote_addr} - POST /files/uploadLastCreated - CRD_ID: {crd_id}"
            )
    except Exception as e:
        app_logger.error(
            f"{request.remote_addr} - POST /files/uploadLastCreated - Error: {e}"
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()

    try:
        video_path: str = file_config.get_newest_file()
        app_logger.info(
            f"{request.remote_addr} - POST /files/uploadLastCreated - OK - New file found: {video_path}"
        )

        # Read the file and erase from disk
        with open(video_path, "br") as f:
            new_video = f.read()
        file_config.delete_all_files()
        app_logger.info(
            f"{request.remote_addr} - POST /files/uploadLastCreated - OK - File read & erased: {video_path}"
        )

        # Encrypt the file
        video_encrypted = security_config.encryptor_backend.encrypt_object(new_video)
        app_logger.info(
            f"{request.remote_addr} - POST /files/uploadLastCreated - OK - File encrypted"
        )

        # Save in MongoDB
        file_name = f"{crd_id}_{get_now_standard()}.{video_format}"
        video_act = VideoActionsMongoDB(crd_id=crd_id, filename=file_name)
        response = video_act.insert_video(video_encrypted)
        app_logger.info(
            f"{request.remote_addr} - POST /files/uploadLastCreated - OK - File saved in MongoDB: {file_name}"
        )

        # Log the video upload
        if response.success:
            app_logger.info(
                f"{request.remote_addr} - POST /files/uploadLastCreated - 200 - Video recorded and upload"
            )
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Video recorded and upload: {file_name}",
            ).save()
            return BasicResponse(
                success=True, status_code=200, message="Video recorded & Saved"
            ).model_dump_json()
        else:
            app_logger.error(
                f"{request.remote_addr} - POST /files/uploadLastCreated - 501 - Video Recorded but not uploaded"
            )
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_error,
                message=f"Video Recorded but not uploaded: {file_name}",
            ).save()
            return BasicResponse(
                success=True,
                status_code=501,
                message="Video recorded but not uploaded.",
            ).model_dump_json()
    except Exception or ConnectionError as e:
        # Add a log
        app_logger.error(
            f"{request.remote_addr} - POST /files/uploadLastCreated - 500 - Error: Upload fail because {e}"
        )
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


def send_video_frame_as_json(video_path: str, frame_number: int = 0) -> BasicResponse:
    """
    Extract a frame from an MP4 video and send it to the frontend as a JSON response.
    @param: video_path: Path to the MP4 video file
    @param: frame_number: Frame number to extract (default is the first frame)
    @return: JSON response containing the frame data
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /video/digicam/preview" -')

    cap = None
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)

        # Set the frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        # Read the frame
        ret, frame = cap.read()

        # Check if the frame is successfully read
        if not ret:
            app_logger.error(
                f'{request.remote_addr} - "GET /video/digicam/preview" - 501 - Error reading frame from video'
            )

            return BasicResponse(
                success=False, status_code=501, message="Error reading frame from video"
            )

        # Convert the frame to base64 for sending in JSON
        _, buffer = cv2.imencode(".jpg", frame)
        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        frame_response = {"frame_number": frame_number, "frame_base64": frame_base64}
        frame_data_response = DataResponse(
            success=True,
            status_code=200,
            message="Frame for preview",
            data=frame_response,
        )

        app_logger.info(
            f'{request.remote_addr} - "GET /video/digicam/preview" - OK - Frame for preview'
        )
        return frame_data_response

    except (Exception, ConnectionError, IOError) as e:
        app_logger.error(
            f'{request.remote_addr} - "GET /video/digicam/preview" - 500 - Error: {e}'
        )
        return BasicResponse(
            sucess=False,
            status_code=500,
            message=f"Error sending frame for previsualitation: {e}",
        )

    finally:
        # Release the video capture object
        if cap:
            cap.release()


@bp_video.route("/video/uploads", methods=["POST"])
@jwt_required()
@cross_origin()
def upload_video(save_test: bool = True) -> str:
    """
    Endpoint to upload a video file to the server.
    :return: A BasicResponse with a message and a status code.
    """
    app_logger.info(f'127.0.0.1 - - [{get_now_standard()}] "POST /video/uploads"')
    try:
        # Get the video file from the request
        video = request.files.get("video")

        video_buffer = video.stream.read()
        video_encrypted = security_config.encryptor_backend.encrypt_object(video_buffer)

        # Get the data from the request body
        crd_id = request.form.get("crd_id", "UNK")
        patient_id = request.form.get("patient_id", "UNK")
        file_name = request.form.get(
            "file_name", f"{crd_id}--{patient_id}--{get_now_standard()}.mkv"
        )

        # Log the data from the request
        app_logger.info(
            f"FrontEnd: Data send - CRD: {crd_id} - Patient: {patient_id} - File: {file_name}"
        )

        if save_test:
            # Save the video file as a new file
            os.makedirs(file_config.uploads_path, exist_ok=True)
            path_video = os.path.join(file_config.uploads_path, file_name)
            with open(path_video, "wb") as f:
                f.write(video_buffer)
            app_logger.info(
                f"BackEnd: Video saved - CRD: {crd_id} - Patient: {patient_id} - File: {path_video}"
            )

        # Create a VideoAction
        video_act = VideoActionsMongoDB(
            crd_id=crd_id, patient_id=patient_id, filename=file_name
        )
        # Save the video path to MongoDB
        response = video_act.insert_video(video_encrypted)

        # Log the video upload
        if response.success:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Video uploaded: {file_name}",
            ).save()
            app_logger.info(
                f"BackEnd: Video uploaded - CRD: {crd_id} - Patient: {patient_id} - File: {file_name}"
            )
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_error,
                message=f"Video not uploaded: {file_name}",
            ).save()
            app_logger.error(
                f"BackEnd: Video not uploaded - CRD: {crd_id} - Patient: {patient_id} - File: {file_name}"
            )

    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

        # Add a log
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        app_logger.info(
            f'127.0.0.1 - - [{get_now_standard()}] "POST /video/uploads" - {response.model_dump_json()}'
        )

    return response.model_dump_json()


@bp_video.route("/video/downloadBy", methods=["GET"])
def download_video():
    """
    Endpoint to download a video file from the server.
    :return:
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /video/downloadBy" -')

    try:
        # Get the data from the request
        data = request.args
        # Get data from request body
        query = {key: value for key, value in data.items() if value != ""}
        # Create a VideoAction
        videos_obj = VideoActionsMongoDB.get_videos_by(query)

        if videos_obj.success and videos_obj.data:
            # Get the video file
            videos_found: list = []
            for obj_mongo in videos_obj.data:
                video_name = obj_mongo.get("filename")
                videos_found.append(video_name)

                file_mongo = obj_mongo.get("file")
                video_encrypted = file_mongo.read()
                video = security_config.encryptor_backend.decrypt_object(
                    video_encrypted
                )

                # Write the video file to a specified path
                if not file_config.exists():
                    os.makedirs(file_config.uploads_path, exist_ok=True)
                video_path = os.path.join(file_config.uploads_path, video_name)
                with open(video_path, "wb") as f:
                    f.write(video)

                # Get the properties of the video downloaded
                get_video_properties(video_path)

            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Video/s downloaded successfully: {videos_found}",
            ).save()
            app_logger.info(
                f'{request.remote_addr} - "GET /video/downloadBy" - '
                f"OK - Video/s downloaded successfully: {videos_found}"
            )

            response = ListResponse(
                success=True,
                status_code=200,
                message="Videos downloaded successfully",
                data=videos_found,
            )
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_warning,
                message=f"Video/s not found: {query}",
            ).save()
            app_logger.warning(
                f'{request.remote_addr} - "GET /video/downloadBy" - 400 - Video/s not found: {query}'
            )

            response = BasicResponse(
                success=False, status_code=400, message="Video/s not found"
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        app_logger.error(
            f'{request.remote_addr} - "GET /video/downloadBy" - 500 - Error: {e}'
        )

        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


# Backup Section
@bp_video.route("/backup/make", methods=["GET"])
@cross_origin()
def make_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /backup/make" -')

    try:
        if backup.mongo_dump():
            app_logger.info(
                f'{request.remote_addr} - "GET /backup/make" - OK - Backup created successfully'
            )
            response = BasicResponse(
                success=True,
                status_code=200,
                message="Backup created successfully",
            )
        else:
            app_logger.error(
                f'{request.remote_addr} - "GET /backup/make" - 400 - Backup not created'
            )
            response = BasicResponse(
                success=False, status_code=400, message="Backup not created"
            )
    except Exception as e:
        app_logger.error(
            f'{request.remote_addr} - "GET /backup/make" - 500 - Error: {e}'
        )
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


@bp_video.route("/backup/restore", methods=["GET"])
@cross_origin()
def restore_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "GET /backup/restore" -')

    try:
        backup_date = request.args.get("date", "")
        if backup.restore(backup_date):
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Backup restored successfully: {backup_date}",
            ).save()
            app_logger.info(
                f'{request.remote_addr} - "GET /backup/restore" - OK - Backup restored successfully: {backup_date}'
            )

            response = BasicResponse(
                success=True,
                status_code=200,
                message="Backup restored successfully",
            )
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_warning,
                message=f"Backup not restored: {backup_date}",
            ).save()
            app_logger.warning(
                f'{request.remote_addr} - "GET /backup/restore" - 400 - Backup not restored: {backup_date}'
            )

            response = BasicResponse(
                success=False, status_code=400, message="Backup not restored"
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        app_logger.error(
            f'{request.remote_addr} - "GET /backup/restore" - 500 - Error: {e}'
        )

        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()

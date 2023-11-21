import base64
import os
import time

import cv2
from flask import Flask, request, redirect, send_from_directory
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
)
from flask_mongoengine import MongoEngine
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from camera.cam import Camera
from config.backend_config import (
    BasicMongoConfig,
    BasicSecurityConfig,
    BasicServerConfig,
    logger,
)
from database.basic_mongo import *
from frontData.basic_record_types import BasicRecordSessionData
from log.basic_log_types import (
    LogOrigins,
    log_type_warning,
    log_type_info,
    log_type_error,
)
from responses.basic_responses import (
    DataResponse,
    BasicResponse,
    ListResponse,
    TokenResponse,
)
from utils.backup import BackUp
from utils.files import check_for_new_files, get_video_properties, BasicFileConfig
from utils.utils import get_now_standard

# Initialize Flask
app = Flask(__name__)

# Configure BackEnd
flask_app = BasicServerConfig(
    path_to_config=os.path.join(os.getcwd(), "secrets", "backend_config.json")
)

# Configure FrontEnd
react_app = BasicServerConfig(
    path_to_config=os.path.join(os.getcwd(), "secrets", "frontend_config.json")
)
react_app.load_config()

# Configure MongoDB
mongo_config = BasicMongoConfig(path_to_config=os.path.join(os.getcwd(), "secrets"))
mongo_config.load_credentials()
app.config["MONGODB_SETTINGS"] = mongo_config.model_dump()
# Initialize MongoDB
mongo = MongoEngine()
mongo.init_app(app)

# Set the secret key to enable JWT authentication
security_config = BasicSecurityConfig(
    path_to_secrets=os.path.join(os.getcwd(), "secrets")
)
app.config["JWT_SECRET_KEY"] = security_config.secret
jwt = JWTManager(app)

# Create a backup
backup = BackUp(mongo_config)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": f"{react_app.host}:{react_app.port}"}})

# Check the server status
logger.info("*** Starting the backend ***")
logger.info("--- Checking the server status ---")
logger.info(
    f"MongoDB: http://{mongo_config.host}:{mongo_config.port}"
    f' - Status: {"UP" if mongo_config.server_is_up() else "DOWN"}'
)
logger.info(
    f'UI: {react_app.host}:{react_app.port} - Status: {"UP" if react_app.server_is_up() else "DOWN"}'
)

# Configure the camera if a config file is present
camera = Camera()


# Endpoints Section
@app.errorhandler(404)
def resource_not_found():
    """
    An error-handler to ensure that 404 errors are returned as JSON.
    :return: A BasicResponse representing a 404 error.
    """
    response = BasicResponse(
        success=False,
        status_code=404,
        message=f"Resource not found: {request.url}",
    )
    return response.model_dump()


@app.errorhandler(DuplicateKeyError)
def resource_not_found(e):
    """
    An error-handler to ensure that MongoDB duplicate key errors are returned as JSON.
    :return: A BasicResponse representing a duplicate key error from MongoDB.
    """
    response = BasicResponse(
        success=False,
        status_code=500,
        message=f"Duplicate key error: {str(e)}",
    )
    return response.model_dump_json()


@app.route("/")
@cross_origin()
def index():
    """
    A simple endpoint with a welcome message from the Backend.
    :return: A welcome message from the Backend.
    """
    return "Welcome to the backend!"


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/poll")
@cross_origin()
def poll():
    """
    A simple endpoint to test the connection with the Backend
    :return: A BasicResponse with the status of the Backend
    """
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


@app.route("/login/addUser", methods=["POST"])
def add_user():
    """
    Endpoint to add a user to the MongoDB database.
    """
    try:
        username = request.json.get("username", False)
        password = request.json.get("password", False)
        if username and password:
            user = UserDocument(
                username=username,
                password=security_config.encryptor_backend.encrypt_object(password),
            )
            user.save()
            response = BasicResponse(
                success=True,
                status_code=200,
                message="User added successfully",
            )
        else:
            response = BasicResponse(
                success=False, status_code=400, message="Bad request"
            )
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


# Security Section


@app.route("/requestAccessTokenByUser", methods=["POST"])
@cross_origin()
def get_access_token_by_user():
    """
    Endpoint to get an access token from the Backend.
    :return: A JSON object with a message and a status code.
    """
    try:
        user_name = request.json.get("username", "UNK")
        user_pass = request.json.get("password", "UNK")
        front_user = UserDocument.objects(username=user_name).first()

        if user_pass == security_config.encryptor_backend.decrypt_object(
            front_user.password
        ):
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Successful login: {user_name}",
            ).save()

            access_token = create_access_token(identity=user_name)
            refresh_token = create_refresh_token(identity=user_name)
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Tokens created successfully: {user_name}",
            ).save()

            response = TokenResponse(
                success=True,
                status_code=200,
                message="Tokens created successfully",
                access_token=access_token,
                refresh_token=refresh_token,
            )
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_warning,
                message=f"Invalid credentials: {user_name}",
            ).save()
            response = BasicResponse(
                success=False, status_code=401, message="Invalid credentials"
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=f"Error: {e}",
        ).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


# Log Section
@app.route("/log/addLogFrontEnd", methods=["POST"])
@cross_origin()
def upload_log_frontend() -> str:
    """
    Endpoint to log data from the FrontEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request body
    log_type = request.json.get("log_type")
    message = request.json.get("message")

    response = LogActionsMongoDB(
        log_origin=LogOrigins.FRONTEND.value,
        log_type=log_type,
        message=message,
    ).insert_log()
    return response.model_dump_json()


@app.route("/log/addLogBackEnd", methods=["POST"])
def upload_log_backend() -> str:
    """
    Endpoint to log data from the BackEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request body
    log_type = request.json.get("log_type")
    message = request.json.get("message")

    response = LogActionsMongoDB(
        log_origin=LogOrigins.BACKEND.value, log_type=log_type, message=message
    ).insert_log()
    return response.model_dump_json()


# Endpoint to retrieve logs by type
@app.route("/log/getLogsBy", methods=["GET"])
@cross_origin()
def get_logs_by() -> str:
    """
    Endpoint to retrieve logs from the MongoDB database based on specified filters.
    We use a dictionary containing filter criteria, if one of the is empty we ignore and use the others, e.g.,
     {'log_type': 'DEBUG', 'log_origin': 'BACKEND'., 'id': '096asdf'}
    :return: A JSON object with a list of logs or a message and a status code.
    """
    try:
        # Get data from request
        data = request.args
        # Get data from request body
        query = {key: value for key, value in data.items() if value != ""}
        # Create a Log Action
        response = LogActionsMongoDB.get_logs_by_type(query)

    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


# Render section
record_data = BasicRecordSessionData(crd_id="001-T-CRD", ov=1)


# Render functions for the frontend
@app.route("/render/getRecordData")
@cross_origin()
def get_record_session_data():
    try:
        response = DataResponse(
            success=True,
            status_code=200,
            message="Data for Record-Session is ready",
            data=record_data.model_dump(),
        )
    except ValueError as e:
        response = DataResponse(
            success=False,
            status_code=400,
            message=f"Value Error: {e}",
            data={},
        )
    except Exception as e:
        response = DataResponse(
            success=False, status_code=400, message=f"Error: {e}", data={}
        )

    return response.model_dump()


@app.route("/video", methods=["GET"])
@cross_origin()
def get_render_video():
    """
    Endpoint to render a video file from a get request.
    :return: a redirection to the VideoRecording Frontend service.
    """
    try:
        # Get data from request
        record_data.crd_id = request.args.get("crd", "UNK")
        record_data.ov = request.args.get("ov", "UNK")
        # Add a log
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_info,
            message=f"Video requested: {record_data.crd_id}--{record_data.ov}",
        ).save()
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
    return redirect(f"{react_app.host}:{react_app.port}/")


# Data Handler Section
file_config = BasicFileConfig()
file_config.update_upload_files()


@app.route("/video/digicam/makeVideo", methods=["GET"])
# @jwt_required()
@cross_origin()
def record_video(duration: float = 10) -> str:
    """
    Endpoint to record a video file using DigicamControl.
    @param duration: The duration of the video in seconds.
    """
    logger.info(f'{request.remote_addr} - "GET /video/digicam/makeVideo" -')
    if not camera.is_running():
        logger.warning(
            f'{request.remote_addr} - "GET /video/digicam/makeVideo" - digicam isnt running'
        )
        camera.run_digicam()
    try:
        camera_response = camera.start_recording()
        if camera_response.success:
            time.sleep(duration)
            camera_response = camera.stop_recording()

            if camera_response.success:
                # TODO: send video to FrontEnd
                return BasicResponse(
                    success=True, status_code=200, message="Video recorded successfully"
                ).model_dump_json()
        return BasicResponse(
            success=False, status_code=500, message="Video recording fail"
        ).model_dump_json()
    except Exception as e:
        logger.error(
            f'{request.remote_addr} - "GET /video/digicam/makeVideo" - Error {e}'
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@app.route("/video/digicam/startVideo", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_start_video() -> str:
    """
    Endpoint to start recording a video file using DigicamControl.
    @return: A BasicResponse with a message and a status code.
    """
    logger.info(f'{request.remote_addr} - "GET /video/digicam/startVideo"')
    if not camera.is_running():
        logger.warning(
            f'{request.remote_addr} - "GET /video/digicam/startVideo" - digiCam isnt running'
        )
        camera.run_digicam()
    try:
        camera_response = camera.start_recording()
        if camera_response.success:
            logger.info(
                f'{request.remote_addr} - "GET /video/digicam/startVideo" - 200 - digiCam start the recording'
            )
            return BasicResponse(
                success=True,
                status_code=200,
                message="Video recording started",
            ).model_dump_json()
        else:
            logger.error(
                f'{request.remote_addr} - "GET /video/digicam/startVideo" - 500 - digiCam failed to start recording'
            )
            return BasicResponse(
                success=False,
                status_code=400,
                message="Video recording not started",
            ).model_dump_json()
    except Exception as e:
        logger.error(
            f'{request.remote_addr} - "GET /video/digicam/startVideo" - 500 - Error: {e}'
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@app.route("/video/digicam/stopVideo", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_stop_video() -> str:
    """
    Endpoint to stop recording a video file using DigicamControl.
    @return: A BasicResponse with a message and a status code.
    """
    logger.info(f'{request.remote_addr} - "POST /video/digicam/stopVideo"')

    # Save the number of files before recording
    file_config.update_upload_files()

    # Stop the recording
    recording_r: BasicResponse = camera.stop_recording()
    # Log the response
    if recording_r.success:
        logger.info(f"{request.remote_addr} - POST /video/digicam/stopVideo - 200")
    else:
        logger.error(
            f"{request.remote_addr} -POST /video/digicam/stopVideo - 500 - Error: {recording_r.message}"
        )
    return recording_r.model_dump_json()


@app.route("/file/checkFile", methods=["GET"])
# @jwt_required()
@cross_origin()
def check_new_file():
    # Way for the file transferring/storage/etc
    if not file_config.check_for_new_files():
        logger.warning(
            f"{request.remote_addr} - POST /files/checkFiles - WARNING - Nothing found on: {file_config.upload_files}"
        )
        return BasicResponse(
            success=False, status_code=500, message="No new files found"
        ).model_dump_json()

    logger.info(
        f"{request.remote_addr} - POST /files/checkFiles - OK - New file found: {file_config.get_last_created()}"
    )
    return BasicResponse(
        success=True,
        status_code=200,
        message=f"New file found: {file_config.get_last_created()}",
    ).model_dump_json()


@app.route("/file/uploadLastCreated", methods=["POST"])
# @jwt_required()
@cross_origin()
def save_new_file(video_format: str = "mp4") -> str:
    # Check request body
    try:
        crd_id: str = request.json.get("crdId", "UNK")
        if crd_id == "UNK":
            logger.warning(
                f"{request.remote_addr} - POST /video/digicam/stopVideo - CRD_ID missed!!"
            )
        else:
            logger.info(
                f"{request.remote_addr} - POST /video/digicam/stopVideo - CRD_ID: {crd_id}"
            )
    except Exception as e:
        logger.error(
            f"{request.remote_addr} - POST /video/digicam/stopVideo - Error: {e}"
        )
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()

    try:
        video_path: str = file_config.get_last_created()
        logger.info(
            f"{request.remote_addr} - POST /files/checkFiles - OK - New file found: {video_path}"
        )

        # Read the file and erase from disk
        with open(video_path, "br") as f:
            new_video = f.read()
        file_config.delete_all_files()
        logger.info(
            f"{request.remote_addr} - POST /files/checkFiles - OK - File read & erased: {video_path}"
        )

        # Encrypt the file
        video_encrypted = security_config.encryptor_backend.encrypt_object(new_video)
        logger.info(
            f"{request.remote_addr} - POST /files/checkFiles - OK - File encrypted"
        )

        # Save in MongoDB
        file_name = f"{crd_id}_{get_now_standard()}.{video_format}"
        video_act = VideoActionsMongoDB(crd_id=crd_id, filename=file_name)
        response = video_act.insert_video(video_encrypted)
        logger.info(
            f"{request.remote_addr} - POST /files/checkFiles - OK - File saved in MongoDB: {file_name}"
        )

        # Log the video upload
        if response.success:
            logger.info(
                f"{request.remote_addr} - POST /video/digicam/stopVideo - 200 - Video recorded and upload"
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
            logger.error(
                f"{request.remote_addr} - POST /video/digicam/stopVideo - 501 - Video Recorded but not uploaded"
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
        logger.error(
            f"{request.remote_addr} - POST /video/digicam/stopVideo - 500 - Error: Upload fail because {e}"
        )
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        return BasicResponse(
            success=False, status_code=500, message=str(e)
        ).model_dump_json()


@app.route("/video/digicam/preview", methods=["GET"])
# @jwt_required()
@cross_origin()
def digicam_preview():
    """
    Use digicam to record a video and take one frame as a visualization of the camera
    """
    try:
        logger.info(f'{request.remote_addr} - "GET /video/digicam/preview"')
        if not camera.is_running():
            logger.warning(
                f'{request.remote_addr} - "GET /video/digicam/preview" - digicam isnt running'
            )
            camera.run_digicam()

        camera_response = camera.start_recording()
        if camera_response.success:
            file_config.update_upload_files()
            time.sleep(1.5)
            camera_response = camera.stop_recording()

            if camera_response.success:
                # Way for the video transferring
                if check_for_new_files(
                    path_folder=file_config.uploads_path,
                    previous_files=file_config.upload_files,
                    timer_seconds=120,
                ):
                    video_path: str = file_config.get_last_created()
                    response = send_video_frame_as_json(video_path)
                    file_config.delete_all_files()
                    return response.model_dump_json()

        return BasicResponse(
            success=False, status_code=501, message=camera_response.message
        ).model_dump_json()
    except Exception as e:
        logger.error(
            f'{request.remote_addr} - "GET /video/digicam/preview" - Error {e}'
        )
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
        return frame_data_response

    except (Exception, ConnectionError, IOError) as e:
        return BasicResponse(
            sucess=False,
            status_code=500,
            message=f"Error sending frame for previsualitation: {e}",
        )

    finally:
        # Release the video capture object
        if cap:
            cap.release()


@app.route("/video/uploads", methods=["POST"])
@jwt_required()
@cross_origin()
def upload_video(save_test: bool = True) -> str:
    """
    Endpoint to upload a video file to the server.
    :return: A BasicResponse with a message and a status code.
    """
    logger.info(f'127.0.0.1 - - [{get_now_standard()}] "POST /video/uploads"')
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
        logger.info(
            f"FrontEnd: Data send - CRD: {crd_id} - Patient: {patient_id} - File: {file_name}"
        )

        if save_test:
            # Save the video file as a new file
            os.makedirs(file_config.uploads_path, exist_ok=True)
            path_video = os.path.join(file_config.uploads_path, file_name)
            with open(path_video, "wb") as f:
                f.write(video_buffer)
            logger.info(
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
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_error,
                message=f"Video not uploaded: {file_name}",
            ).save()

    except Exception as e:
        # Add a log
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))

    logger.info(
        f'127.0.0.1 - - [{get_now_standard()}] "POST /video/uploads" - {response.model_dump_json()}'
    )
    return response.model_dump_json()


@app.route("/video/downloadBy", methods=["GET"])
def download_video():
    """
    Endpoint to download a video file from the server.
    :return:
    """
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
            response = BasicResponse(
                success=False, status_code=400, message="Video/s not found"
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    """
    Endpoint to test JWT authentication.
    :return: A BasicResponse with a message and a status code.
    """
    response = BasicResponse(success=True, status_code=200, message="Access granted")
    return response.model_dump_json()


# Backup Section
@app.route("/backup/make", methods=["GET"])
@cross_origin()
def make_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    try:
        if backup.make_():
            response = BasicResponse(
                success=True,
                status_code=200,
                message="Backup created successfully",
            )
        else:
            response = BasicResponse(
                success=False, status_code=400, message="Backup not created"
            )
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


@app.route("/backup/restore", methods=["GET"])
@cross_origin()
def restore_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    try:
        backup_date = request.args.get("date", "")
        if backup.restore(backup_date):
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_info,
                message=f"Backup restored successfully: {backup_date}",
            ).save()
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
            response = BasicResponse(
                success=False, status_code=400, message="Backup not restored"
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=str(e),
        ).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


if __name__ == "__main__":
    app.run()

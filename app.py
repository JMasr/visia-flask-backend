import os

from flask import Flask, request, redirect
from flask_cors import CORS
from flask_mongoengine import MongoEngine
from pymongo import MongoClient
from flask_uploads import UploadSet, configure_uploads, ARCHIVES
from pymongo.errors import DuplicateKeyError

from config.backend_config import BasicMongoConfig, BasicSecurityConfig
from database.basic_mongo import LogActionsMongoDB, VideoActionsMongoDB
from frontData.basic_record_types import BasicRecordSessionData
from log.basic_log_types import LogOrigins
from responses.basic_responses import DataResponse, BasicResponse
from security.basic_encription import ObjectEncryptor
from utils.utils import get_now_standard

# from flask_jwt_extended import JWTManager
# from security.basic_security import BasicSecurityHandler

# Initialize Flask
app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Set the secret key to enable JWT authentication
# security_config = BasicSecurityConfig(secret_key='visia@sergas')
# app.config['JWT_SECRET_KEY'] = security_config.secret_key
# jwt = JWTManager(app)

# security_handler = BasicSecurityHandler(security_config.secret_key)


# Sample user data (in a real application, this would come from a database)
# Configure MongoDB
mongo_config = BasicMongoConfig(db='visia_demo', username='rootuser', password='rootpass')
app.config['MONGODB_SETTINGS'] = mongo_config.model_dump()
# Initialize MongoDB
mongo = MongoEngine()
mongo.init_app(app)

# Encryption Section
secrets_path = os.path.join(os.getcwd(), 'secrets/')
security_config = BasicSecurityConfig(secrets_path)
encryptor_object = ObjectEncryptor(key=security_config.secret_key)


# Error handlers
@app.errorhandler(404)
def resource_not_found():
    """
    An error-handler to ensure that 404 errors are returned as JSON.
    """
    response = BasicResponse(success=False, status_code=404, message=f"Resource not found: {request.url}")
    return response.model_dump()


@app.errorhandler(DuplicateKeyError)
def resource_not_found(e):
    """
    An error-handler to ensure that MongoDB duplicate key errors are returned as JSON.
    """
    response = BasicResponse(success=False, status_code=500, message=f"Duplicate key error: {str(e)}")
    return response.model_dump_json()


# Endpoints

# Index
@app.route('/')
def index():  # put application's code here
    return 'Welcome to the backend!'


@app.route('/poll')
def poll():
    """
    A simple endpoint to test the connection with the Backend
    :return: A BasicResponse with the status of the Backend
    """
    try:
        # Initialize a MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
        # Ping the MongoDB server
        is_up = client.admin.command('ping')
        # Close the MongoClient
        client.close()

        if is_up.get("ok") == 1.0:
            response = BasicResponse(success=True, message="Flask and MongoDB are UP!", status_code=200)
        else:
            response = BasicResponse(success=False, message="Flask is UP! and MongoDB is UP but not WORKING!",
                                     status_code=400)
    except (Exception or ConnectionError or TimeoutError):
        response = BasicResponse(success=False, message="Flask is UP! but MongoDB is DOWN!", status_code=503)

    return response.model_dump_json()


# Security Section
# @app.route('/getAccessTokenBySecret', methods=['POST'])
# def get_access_token() -> str:
#     """
#     Endpoint to get an access token.
#     :return: A JSON object with an access token or a message and a status code.
#     """
#     # Get data from request
#     data = request.get_json()
#     try:
#         # Get data from request body
#         secret = data.get('secret')
#         response = security_handler.getAccessToken(secret)
#     except Exception as e:
#         response = BasicResponse(success=False, status_code=500, message=str(e))
#
#     return response.model_dump_json()


# Log Section
def add_log(log_origin: str, log_type: str, message: str) -> BasicResponse:
    """
    Function to log data to MongoDB
    :param log_origin: Origin of the log.
    :param log_type: Type of the log.
    :param message: Message of the log.
    :return: a BasicResponse object with a message and a status code.
    """
    try:
        # Get data from request body
        log_action = LogActionsMongoDB(log_origin=log_origin, log_type=log_type, message=message)
        # Save the log in the database
        response = log_action.insert_log()
    except ValueError as e:
        response = BasicResponse(success=False, status_code=400, message=f'Invalid Value: {e}')
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response


# Endpoint to log data from the frontend
@app.route('/log/addLogFrontEnd', methods=['POST'])
def upload_log_frontend() -> str:
    """
    Endpoint to log data from the FrontEnd
    :return: A JSON object with a message and a status code.
    """
    try:
        # Get data from request
        data = request.get_json()
        # Get data from request body
        log_origin = LogOrigins.FRONTEND
        log_type = data.get('log_type')
        message = data.get('message')

        # Add the log
        response = add_log(log_origin=log_origin.value, log_type=log_type, message=message)
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    # Return the response
    return response.model_dump_json()


@app.route('/log/addLogBackEnd', methods=['POST'])
def upload_log_backend() -> str:
    """
    Endpoint to log data from the BackEnd
    :return: A JSON object with a message and a status code.
    """
    try:
        # Get data from request
        data = request.get_json()
        # Get data from request body
        log_origin = LogOrigins.BACKEND
        log_type = data.get('log_type')
        message = data.get('message')
        # Add the log
        response = add_log(log_origin=log_origin.value, log_type=log_type, message=message)
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    # Return the response
    return response.model_dump_json()


# Endpoint to retrieve logs by type
@app.route('/log/getLogsBy', methods=['GET'])
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
record_data = BasicRecordSessionData(patient_id="001-T-PAT", crd_id="001-T-CRD")


# Render functions for the frontend
@app.route('/getRecordData')
def get_record_session_data():
    try:
        response = DataResponse(success=True, status_code=200, message="Data for Record-Session is ready",
                                data=record_data.model_dump())
    except ValueError as e:
        response = DataResponse(success=False, status_code=400, message=f"Value Error: {e}", data={})
    except Exception as e:
        response = DataResponse(success=False, status_code=400, message=f"Error: {e}", data={})

    return response.model_dump()


@app.route('/video', methods=['GET'])
def get_render_video():
    """
    Endpoint to render a video file from a get request.
    :return: a redirection to the VideoRecording Frontend service.
    """
    try:
        # Get data from request
        record_data.crd_id = request.args.get('crd', "UNK")
        record_data.patient_id = request.args.get('pid', "UNK")

        # Add a log
        add_log(log_origin=LogOrigins.BACKEND.value, log_type="INFO",
                message=f"Successful data capture: {record_data.crd_id} - {record_data.patient_id}")
    except Exception as e:
        # Add a log
        add_log(log_origin=LogOrigins.BACKEND.value, log_type="ERROR", message=str(e))
    return redirect(f"http://localhost:5173/")


# Data Handler Section

# Configure file uploads
upload_files = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOADED_DEFAULT_DEST'] = upload_files  # Change this to your desired upload directory
app.config['UPLOADED_DEFAULT_URL'] = 'http://localhost:5000/uploads/'  # Change this to your server's URL
app.config['UPLOADED_DEFAULT_ALLOW'] = set(ARCHIVES)
app.config['UPLOADED_DEFAULT_DENY'] = set()
uploads = UploadSet('default', extensions=('',))
configure_uploads(app, (uploads,))


@app.route('/video/uploads', methods=['POST'])
def upload_video() -> str:
    """
    Endpoint to upload a video file to the server.
    :return:
    """
    try:
        # Get the video file from the request
        video = request.files['video']

        # Save the video file to a specified path
        # save = os.path.join(upload_files, f"video.filename.webm")

        video_buffer = video.stream.read()
        video_encrypted = encryptor_object.encrypt_object(video_buffer)

        # Get the data from the request body
        crd_id = request.form.get('crd_id', "UNK")
        patient_id = request.form.get('patient_id', "UNK")
        file_name = request.form.get('file_name', f"{crd_id}_{patient_id}--{get_now_standard()}.wbm")

        # Create a VideoAction
        video_act = VideoActionsMongoDB(crd_id=crd_id, patient_id=patient_id, filename=file_name)
        # Save the video path to MongoDB
        response = video_act.insert_video(video_encrypted)

        # Log the video upload
        if response.success:
            add_log(log_origin=LogOrigins.BACKEND.value, log_type="INFO", message=f"Video uploaded: {file_name}")
        else:
            add_log(log_origin=LogOrigins.BACKEND.value, log_type="ERROR", message=response.message)

    except Exception as e:
        # Add a log
        add_log(log_origin=LogOrigins.BACKEND.value, log_type="ERROR", message=str(e))
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


@app.route('/video/downloadBy', methods=['GET'])
def download_video():
    """
    Endpoint to download a video file from the server.
    :return:
    """
    try:
        # Get tghe data from the request
        data = request.args
        # Get data from request body
        query = {key: value for key, value in data.items() if value != ""}
        # Create a VideoAction
        videos_obj = VideoActionsMongoDB.get_videos_by(query)

        # TODO: Create a function to download all the videos on videos_obj
        if videos_obj.success and videos_obj.data:
            # Get the video file
            video_file = [video.get("file") for video in videos_obj.data]
            video_encrypted = video_file[0]
            video = encryptor_object.decrypt_object(video_encrypted)

            # Write the video file to a specified path
            if not os.path.exists(upload_files):
                os.makedirs(upload_files)

            file_name = 'video.webm'
            file_path = os.path.join(upload_files, file_name)
            with open(file_path, 'wb') as f:
                f.write(video)

            response = BasicResponse(success=True, status_code=200, message="Video downloaded successfully")
        else:
            response = BasicResponse(success=False, status_code=400, message="Video/s not found")

    except Exception as e:
        # Add a log
        add_log(log_origin=LogOrigins.BACKEND.value, log_type="ERROR", message=str(e))
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


if __name__ == '__main__':
    app.run(debug=True)

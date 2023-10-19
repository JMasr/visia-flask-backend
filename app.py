import os

from flask import Flask, request, redirect
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required
from flask_mongoengine import MongoEngine
from flask_uploads import UploadSet, configure_uploads, ARCHIVES
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from config.backend_config import BasicMongoConfig, BasicSecurityConfig
from database.basic_mongo import *
from frontData.basic_record_types import BasicRecordSessionData
from log.basic_log_types import LogOrigins, log_type_warning, log_type_info, log_type_error
from responses.basic_responses import DataResponse, BasicResponse, ListResponse, TokenResponse
from utils.backup import BackUp
from utils.utils import get_now_standard

# Initialize Flask
app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Set the secret key to enable JWT authentication
security_config = BasicSecurityConfig(path_to_secrets=os.path.join(os.getcwd(), 'secrets'))
app.config['JWT_SECRET_KEY'] = security_config.secret
jwt = JWTManager(app)

# Configure MongoDB
mongo_config = BasicMongoConfig(credentials=os.path.join(os.getcwd(), 'secrets'))
mongo_config.load_credentials()
app.config['MONGODB_SETTINGS'] = mongo_config.model_dump()
# Initialize MongoDB
mongo = MongoEngine()
mongo.init_app(app)

# Create a backup
backup = BackUp(mongo_config)


# Endpoints Section
@app.errorhandler(404)
def resource_not_found():
    """
    An error-handler to ensure that 404 errors are returned as JSON.
    :return: A BasicResponse representing a 404 error.
    """
    response = BasicResponse(success=False, status_code=404, message=f"Resource not found: {request.url}")
    return response.model_dump()


@app.errorhandler(DuplicateKeyError)
def resource_not_found(e):
    """
    An error-handler to ensure that MongoDB duplicate key errors are returned as JSON.
    :return: A BasicResponse representing a duplicate key error from MongoDB.
    """
    response = BasicResponse(success=False, status_code=500, message=f"Duplicate key error: {str(e)}")
    return response.model_dump_json()


@app.route('/')
def index():
    """
    A simple endpoint with a welcome message from the Backend.
    :return: A welcome message from the Backend.
    """
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


@app.route('/login/addUser', methods=['POST'])
def add_user():
    """
    Endpoint to add a user to the MongoDB database.
    """
    try:
        username = request.json.get('username', False)
        password = request.json.get('password', False)
        if username and password:
            user = UserDocument(username=username, password=security_config.encryptor_backend.encrypt_object(password))
            user.save()
            response = BasicResponse(success=True, status_code=200, message="User added successfully")
        else:
            response = BasicResponse(success=False, status_code=400, message="Bad request")
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


# Security Section

@app.route('/requestAccessTokenByUser', methods=['POST'])
def get_access_token_by_user():
    """
    Endpoint to get an access token from the Backend.
    :return: A JSON object with a message and a status code.
    """
    try:
        user_name = request.json.get('username', "UNK")
        user_pass = request.json.get('password', "UNK")
        front_user = UserDocument.objects(username=user_name).first()

        if user_pass == security_config.encryptor_backend.decrypt_object(front_user.password):
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Successful login: {user_name}").save()

            access_token = create_access_token(identity=user_name)
            refresh_token = create_refresh_token(identity=user_name)
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Tokens created successfully: {user_name}").save()

            response = TokenResponse(success=True, status_code=200, message="Tokens created successfully",
                                     access_token=access_token, refresh_token=refresh_token)
        else:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_warning,
                        message=f"Invalid credentials: {user_name}").save()
            response = BasicResponse(success=False, status_code=401, message="Invalid credentials")
    except Exception as e:
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error,
                    message=f"Error: {e}").save()
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


# Log Section
@app.route('/log/addLogFrontEnd', methods=['POST'])
def upload_log_frontend() -> str:
    """
    Endpoint to log data from the FrontEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request body
    log_type = request.json.get('log_type')
    message = request.json.get('message')

    response = LogActionsMongoDB(log_origin=LogOrigins.FRONTEND.value, log_type=log_type, message=message).insert_log()
    return response.model_dump_json()


@app.route('/log/addLogBackEnd', methods=['POST'])
def upload_log_backend() -> str:
    """
    Endpoint to log data from the BackEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request body
    log_type = request.json.get('log_type')
    message = request.json.get('message')

    response = LogActionsMongoDB(log_origin=LogOrigins.BACKEND.value, log_type=log_type, message=message).insert_log()
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
@app.route('/render/getRecordData')
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
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                    message=f"Video requested: {record_data.crd_id}--{record_data.patient_id}").save()
    except Exception as e:
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error, message=str(e)).save()
    return redirect(f"http://localhost:5173/")


# Data Handler Section
upload_files = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOADED_DEFAULT_DEST'] = upload_files  # Change this to your desired upload directory
app.config['UPLOADED_DEFAULT_URL'] = 'http://localhost:5000/uploads/'  # Change this to your server's URL
app.config['UPLOADED_DEFAULT_ALLOW'] = set(ARCHIVES)
app.config['UPLOADED_DEFAULT_DENY'] = set()
uploads = UploadSet('default', extensions=('',))
configure_uploads(app, (uploads,))


@app.route('/video/uploads', methods=['POST'])
@jwt_required()
def upload_video() -> str:
    """
    Endpoint to upload a video file to the server.
    :return: A BasicResponse with a message and a status code.
    """
    try:
        # Get the video file from the request
        video = request.files.get('video')

        # Save the video file to a specified path
        # save = os.path.join(upload_files, f"video.filename.webm")

        video_buffer = video.stream.read()
        video_encrypted = security_config.encryptor_backend.encrypt_object(video_buffer)

        # Get the data from the request body
        crd_id = request.form.get('crd_id', "UNK")
        patient_id = request.form.get('patient_id', "UNK")
        file_name = request.form.get('file_name', f"{crd_id}--{patient_id}--{get_now_standard()}.webm")

        # Create a VideoAction
        video_act = VideoActionsMongoDB(crd_id=crd_id, patient_id=patient_id, filename=file_name)
        # Save the video path to MongoDB
        response = video_act.insert_video(video_encrypted)

        # Log the video upload
        if response.success:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Video uploaded: {file_name}").save()
        else:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error,
                        message=f"Video not uploaded: {file_name}").save()

    except Exception as e:
        # Add a log
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error, message=str(e)).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


@app.route('/video/downloadBy', methods=['GET'])
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
                video = security_config.encryptor_backend.decrypt_object(video_encrypted)

                # Write the video file to a specified path
                if not os.path.exists(upload_files):
                    os.makedirs(upload_files)
                file_path = os.path.join(upload_files, video_name)
                with open(file_path, 'wb') as f:
                    f.write(video)

            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Video/s downloaded successfully: {videos_found}").save()
            response = ListResponse(success=True, status_code=200, message="Videos downloaded successfully",
                                    data=videos_found)
        else:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_warning,
                        message=f"Video/s not found: {query}").save()
            response = BasicResponse(success=False, status_code=400, message="Video/s not found")
    except Exception as e:
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error, message=str(e)).save()
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
@app.route('/backup/make', methods=['GET'])
def make_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    try:
        if backup.make():
            response = BasicResponse(success=True, status_code=200, message="Backup created successfully")
        else:
            response = BasicResponse(success=False, status_code=400, message="Backup not created")
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


@app.route('/backup/restore', methods=['GET'])
def restore_backup():
    """
    Endpoint to make a backup of the database.
    :return: A BasicResponse with a message and a status code.
    """
    try:
        backup_date = request.args.get('date', '')
        if backup.restore(backup_date):
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_info,
                        message=f"Backup restored successfully: {backup_date}").save()
            response = BasicResponse(success=True, status_code=200, message="Backup restored successfully")
        else:
            LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_warning,
                        message=f"Backup not restored: {backup_date}").save()
            response = BasicResponse(success=False, status_code=400, message="Backup not restored")
    except Exception as e:
        LogDocument(log_origin=LogOrigins.BACKEND.value, log_type=log_type_error, message=str(e)).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))
    return response.model_dump_json()


if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, request
from flask_cors import CORS
from flask_mongoengine import MongoEngine
from pymongo.errors import DuplicateKeyError

from config.backend_config import BasicMongoConfig
from database.basic_mongo import LogActionsMongoDB
from frontData.basic_record_types import BasicRecordSessionData
from log.basic_log_types import LogOrigins
from responses.basic_responses import DataResponse, BasicResponse

# Initialize Flask
app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Configure MongoDB
mongo_config = BasicMongoConfig(db='visia_demo', username='admin', password='admin')
app.config['MONGODB_SETTINGS'] = mongo_config.model_dump()
# Initialize MongoDB
mongo = MongoEngine()
mongo.init_app(app)


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


@app.route('/')
def index():  # put application's code here
    return 'Welcome to the backend!'


# Log Section
# Endpoint to log data from the frontend
@app.route('/log/addLogFrontEnd', methods=['POST'])
def add_log_frontend() -> str:
    """
    Endpoint to log data from the FrontEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request
    data = request.get_json()

    try:
        # Get data from request body
        log_origin = data.get('origin', LogOrigins.FRONTEND)  # Default to backend if not provided
        log_type = data.get('log_type')
        message = data.get('message')

        # Create a Log Action
        log_action = LogActionsMongoDB(log_origin=log_origin, log_type=log_type, message=message)
        # Save the log in the database
        response = log_action.insert_log()
    except ValueError as e:
        response = BasicResponse(success=False, status_code=400, message=f'Invalid Value: {e}')
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    # Return the response
    return response.model_dump_json()


@app.route('/log/addLogBackEnd', methods=['POST'])
def add_log_backend() -> str:
    """
    Endpoint to log data from the BackEnd
    :return: A JSON object with a message and a status code.
    """
    # Get data from request
    data = request.get_json()

    try:
        # Get data from request body
        log_origin = data.get('origin', LogOrigins.BACKEND)  # Default to backend if not provided
        log_type = data.get('log_type')
        message = data.get('message')

        # Create a Log Action
        log_action = LogActionsMongoDB(log_origin=log_origin, log_type=log_type, message=message)
        # Save the log in the database
        response = log_action.insert_log()
    except ValueError as e:
        response = BasicResponse(success=False, status_code=400, message=f'Invalid Value: {e}')
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    # Return the response
    return response.model_dump_json()


# Endpoint to retrieve logs by type
@app.route('/log/getLogsBy', methods=['GET'])
def get_logs_by_type() -> str:
    """
    Endpoint to retrieve logs from the MongoDB database based on specified filters.
    We use a dictionary containing filter criteria, if one of the is empty we ignore and use the others, e.g.,
     {'log_type': 'DEBUG', 'log_origin': 'BACKEND'., 'id': '096asdf'}
    :return: A JSON object with a list of logs or a message and a status code.
    """
    # Get data from request
    data = request.args

    try:
        # Get data from request body
        query = {key: value for key, value in data.items() if value != ""}
        # Create a Log Action
        response = LogActionsMongoDB.get_logs_by_type(query)

    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))

    return response.model_dump_json()


# Render functions for the frontend
## Render the Record-Session data
@app.route('/getRecordData')
def get_record_session_data():
    try:
        session_data = BasicRecordSessionData(patient_id="001-T-PAT", crd_id="001-T-CRD")
        response = DataResponse(success=True, status_code=200, message="Data for Recorod-Session is ready",
                                data=session_data.model_dump())
    except ValueError as e:
        response = DataResponse(success=False, status_code=400, message=f"Value Error: {e}", data={})
    except Exception as e:
        response = DataResponse(success=False, status_code=400, message=f"Error: {e}", data={})

    return response.model_dump()


if __name__ == '__main__':
    app.run(debug=True)

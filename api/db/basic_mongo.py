from datetime import datetime

from pydantic import BaseModel
from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    EnumField,
    FileField,
)

from api.log.basic_log_types import LogOrigins, LogTypes
from api.responses.basic_responses import BasicResponse, DataResponse, ListResponse


# MongoDB data models
class LogDocument(Document):
    """
    Log Document to store log data in MongoDB. Receive logs from the backend or frontend and store them in MongoDB.
    :param log_origin: Origin of the log.
    :param log_type: Type of the log.
    :param message: Message of the log.
    :param timestamp: Timestamp of the log.
    """

    log_type = EnumField(LogTypes, required=True)
    log_origin = EnumField(LogOrigins, required=True)
    message = StringField(required=True)
    timestamp = DateTimeField(default=datetime.now())


class VideoDocument(Document):
    # Metadata
    crd_id = StringField(required=True)
    timestamp = DateTimeField(default=datetime.now())
    # Video
    filename = StringField(required=True)
    _file = FileField(required=True)

    def get_video(self):
        """
        Get the file from the VideoDocument.
        :return: A binary file.
        """
        return self._file


class UserDocument(Document):
    username = StringField(required=True)
    password = StringField(required=True)


# MongoDB actions
class LogActionsMongoDB(BaseModel):
    """
    Class to perform actions on the MongoDB database.
    :param log_origin: Receive the origin of the log (backend or frontend).
    :param log_type: Receive the type of the log (debug, error, info or warning).
    :param message: Receive an informative message of the log.
    """

    log_origin: LogOrigins
    log_type: LogTypes
    message: str

    def insert_log(self) -> BasicResponse:
        """
        Insert a Log Object in the MongoDB database.
        """
        try:
            # Create a Log Document
            new_log = LogDocument(
                log_origin=self.log_origin,
                log_type=self.log_type,
                message=self.message,
            )
            # Save the log in the database
            id_mongo_db = new_log.save()
            id_log = str(id_mongo_db.id)
            # Set the id of the log
            response = DataResponse(
                success=True,
                status_code=200,
                message="Log added: successfully",
                data={"id": id_log},
            )
        except ValueError as e:
            response = BasicResponse(
                success=False, status_code=400, message=f"Invalid Value: {e}"
            )
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response

    @staticmethod
    def get_logs_by_type(query: dict[str, str]) -> BasicResponse:
        """
        Get logs from the MongoDB database based on specified filters.
        :param query: A dictionary containing filter criteria, e.g., {'log_type': 'error', 'log_origin': 'backend'}
        :return: A JSON object with a message and a status code.
        """
        try:
            # Retrieve logs based on the query from MongoDB
            logs = LogDocument.objects(**query)

            log_data = [
                {
                    "id": str(log.id),
                    "log_type": log.log_type,
                    "message": log.message,
                    "log_origin": log.log_origin,
                }
                for log in logs
            ]
            response = ListResponse(
                success=True,
                status_code=200,
                message="Logs retrieved successfully",
                data=log_data,
            )

        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response

    @staticmethod
    def upload_log(log_request, log_origin: LogOrigins) -> str:
        """
        Function to handle log data upload from the FrontEnd or BackEnd
        :return: A JSON object with a message and a status code.
        """
        try:
            # Get data from request
            data = log_request.get_json()
            # Get data from request body
            log_type = data.get("log_type")
            message = data.get("message")

            # Add the log
            # Get data from request body
            log_action = LogActionsMongoDB(
                log_origin=log_origin, log_type=log_type, message=message
            )
            # Save the log in the database
            response = log_action.insert_log()
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))

        # Return the response
        return response.model_dump_json()


class VideoActionsMongoDB(BaseModel):
    """
    Class to perform actions with Videos on the MongoDB database.
    :param crd_id: Receive the CRD ID of the video.
    :param filename: Receive the filename of the video.
    """

    # Metadata
    crd_id: str
    # Video
    filename: str

    def insert_video(self, file: bytes) -> BasicResponse:
        """
        Insert a Video Object in the MongoDB database.
        :return: A JSON object with a message and a status code.
        """
        try:
            if file:
                # Create a Video Document
                new_video = VideoDocument(
                    crd_id=self.crd_id,
                    filename=self.filename,
                    _file=file,
                )
                # Save the video in the database
                id_mongo_db = new_video.save()
                id_video = str(id_mongo_db.id)

                # Check if the video has the correct parameters
                if self.crd_id == "UNK" or "UNK" in self.filename:
                    # Handle the case where the video has missing parameters
                    response = DataResponse(
                        success=True,
                        status_code=199,
                        message="Video uploaded, but missing parameters",
                        data={"id": id_video},
                    )
                else:
                    # Handle the case where the video has all the parameters
                    response = DataResponse(
                        success=True,
                        status_code=200,
                        message="Video added: successfully",
                        data={"id": id_video},
                    )
            else:
                # Handle the case where no file was received
                response = BasicResponse(
                    success=False, status_code=400, message="No file received"
                )
        except ValueError as e:
            # Handle the case where the received file is not a video
            response = BasicResponse(
                success=False, status_code=400, message=f"Invalid Value: {e}"
            )
        except Exception as e:
            # Handle the case where an error occurred
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response

    @staticmethod
    def get_videos_by(query: dict[str, str]) -> BasicResponse:
        """
        Get videos from the MongoDB database based on specified filters.
        :param query: A dictionary containing filter criteria, e.g., {'crd_id': '123456789'}
        :return: A JSON object with a message and a status code.
        """
        try:
            # Create a Video Document
            videos = VideoDocument.objects(**query)
            video_data = [
                {
                    "id": str(video.id),
                    "crd_id": video.crd_id,
                    "filename": video.filename,
                    "file": video.get_video(),
                }
                for video in videos
            ]
            response = ListResponse(
                success=True,
                status_code=200,
                message="Videos retrieved successfully",
                data=video_data,
            )
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response


class UserActionMongoDB(BaseModel):
    """
    Class to perform actions with Users on the MongoDB database.
    """

    username: str
    password: str

    def insert_user(self) -> BasicResponse:
        """
        Insert a User Object in the MongoDB database.
        :return: A JSON object with a message and a status code.
        """
        try:
            # Create a User Document
            new_user = UserDocument(username=self.username, password=self.password)
            # Save the user in the database
            id_mongo_db = new_user.save()
            id_user = str(id_mongo_db.id)
            # Set the id of the user
            response = DataResponse(
                success=True,
                status_code=200,
                message="User added: successfully",
                data={"id": id_user},
            )
        except ValueError as e:
            response = BasicResponse(
                success=False, status_code=400, message=f"Invalid Value: {e}"
            )
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response

    def get_user(self) -> BasicResponse:
        """
        Get a User Object from the MongoDB database.
        :return: A JSON object with a message and a status code.
        """
        try:
            # Retrieve user based on the query from MongoDB
            user = UserDocument.objects(username=self.username)
            user_data = [
                {
                    "id": str(user.id),
                    "username": user.username,
                    "password": user.password,
                }
                for user in user
            ]
            response = ListResponse(
                success=True,
                status_code=200,
                message="User retrieved successfully",
                data=user_data,
            )
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))
        # Return the response
        return response

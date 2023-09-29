from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, EnumField
from pydantic import BaseModel

from log.basic_log_types import LogOrigins, LogTypes
from responses.basic_responses import BasicResponse, DataResponse, ListResponse


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
            new_log = LogDocument(log_origin=self.log_origin, log_type=self.log_type, message=self.message)
            # Save the log in the database
            id_mongo_db = new_log.save()
            id_log = str(id_mongo_db.id)
            # Set the id of the log
            response = DataResponse(success=True, status_code=200, message="Log added: successfully",
                                    data={"id": id_log})
        except ValueError as e:
            response = BasicResponse(success=False, status_code=400, message=f'Invalid Value: {e}')
        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))

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
            logs_query = {key: value for key, value in query.items()}
            logs = LogDocument.objects(**logs_query)

            log_data = [
                {"id": str(log.id), "log_type": log.log_type, "message": log.message, "log_origin": log.log_origin}
                for log in logs]
            response = ListResponse(success=True, status_code=200, message="Logs retrieved successfully", data=log_data)

        except Exception as e:
            response = BasicResponse(success=False, status_code=500, message=str(e))

        return response



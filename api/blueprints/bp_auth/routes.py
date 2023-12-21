import os

from flask import Blueprint, request
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token

from api.config.backend_config import BasicSecurityConfig
from api.db.basic_mongo import UserDocument, LogDocument
from api.log import app_logger
from api.log.basic_log_types import LogOrigins, log_type_info, log_type_warning, log_type_error
from api.responses.basic_responses import BasicResponse, TokenResponse

bp_auth = Blueprint("bp_auth", __name__)

# Set the secret key to enable JWT authentication
security_config = BasicSecurityConfig(
    path_to_secrets=os.path.join(os.getcwd(), "secrets")
)


@bp_auth.route("/login/addUser", methods=["POST"])
def add_user():
    """
    Endpoint to add a user to the MongoDB database.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /login/addUser" -')

    try:
        username = request.json.get("username", False)
        password = request.json.get("password", False)

        if username and password:
            user = UserDocument(
                username=username,
                password=security_config.encryptor_backend.encrypt_object(password),
            )

            # Check if the user already exists
            if UserDocument.objects(username=username).first():
                response = BasicResponse(
                    success=True,
                    status_code=200,
                    message="User already exists",
                )
                app_logger.warning(
                    f'{request.remote_addr} - "POST /login/addUser" - OK: User already exists'
                )
            else:
                user.save()
                response = BasicResponse(
                    success=True,
                    status_code=200,
                    message="User added successfully",
                )
                app_logger.info(
                    f'{request.remote_addr} - "POST /login/addUser" - OK: User added successfully'
                )
        else:
            response = BasicResponse(
                success=False, status_code=400, message="Bad request"
            )
            app_logger.info(
                f'{request.remote_addr} - "POST /login/addUser" - ERROR: Bad request'
            )
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
        app_logger.error(
            f'{request.remote_addr} - "POST /login/addUser" - ERROR: {str(e)}'
        )
    return response.model_dump_json()


@bp_auth.route("/login/deleteUser", methods=["POST"])
def delete_user():
    """
    Endpoint to delete a user from the MongoDB database.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /login/deleteUser" -')
    try:
        username = request.json.get("username", False)
        password = request.json.get("password", False)

        if username and password:
            user = UserDocument(
                username=username,
                password=security_config.encryptor_backend.encrypt_object(password),
            )
            user.delete()
            response = BasicResponse(
                success=True,
                status_code=200,
                message="User deleted successfully",
            )
            app_logger.info(
                f'{request.remote_addr} - "POST /login/deleteUser" - OK: User deleted successfully'
            )
        else:
            response = BasicResponse(
                success=False, status_code=400, message="Bad request"
            )
            app_logger.error(
                f'{request.remote_addr} - "POST /login/deleteUser" - ERROR: Bad request'
            )
    except Exception as e:
        response = BasicResponse(success=False, status_code=500, message=str(e))
        app_logger.error(
            f'{request.remote_addr} - "POST /login/deleteUser" - ERROR: {str(e)}'
        )

    return response.model_dump_json()


@bp_auth.route("/requestAccessTokenByUser", methods=["POST"])
@cross_origin()
def get_access_token_by_user():
    """
    Endpoint to get an access token from the Backend.
    :return: A JSON object with a message and a status code.
    """
    # Log the request
    app_logger.info(f'{request.remote_addr} - "POST /requestAccessTokenByUser" -')
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
            app_logger.info(f'{request.remote_addr} - "POST /requestAccessTokenByUser" - OK: Tokens created successfully')
        else:
            LogDocument(
                log_origin=LogOrigins.BACKEND.value,
                log_type=log_type_warning,
                message=f"Invalid credentials: {user_name}",
            ).save()
            response = BasicResponse(
                success=False, status_code=401, message="Invalid credentials"
            )
            app_logger.warning(
                f'{request.remote_addr} - "POST /requestAccessTokenByUser" - ERROR: Invalid credentials'
            )
    except Exception as e:
        LogDocument(
            log_origin=LogOrigins.BACKEND.value,
            log_type=log_type_error,
            message=f"Error: {e}",
        ).save()
        response = BasicResponse(success=False, status_code=500, message=str(e))
        app_logger.error(
            f'{request.remote_addr} - "POST /requestAccessTokenByUser" - ERROR: {str(e)}'
        )
    return response.model_dump_json()

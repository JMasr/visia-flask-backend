# from flask import jsonify, Flask
# from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
#
# from app import app
# from responses.basic_responses import BasicResponse, DataResponse
#
#
# class BasicSecurityHandler:
#     def __init__(self, secret_key):
#         self.secret_key = secret_key
#
#     def getAccessToken(self, secret: str) -> BasicResponse:
#         # Verify the credentials
#         if secret != self.secret_key:
#             response = BasicResponse(success=False, status_code=401, message="Bad credentials")
#         else:
#             # Identity can be any data that is json serializable
#             access_token = create_access_token(identity=secret)
#             response = DataResponse(success=True, status_code=200, message="Login successful",
#                                     data={"access_token": access_token})
#         return response

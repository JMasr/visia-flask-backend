import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mongoengine import MongoEngine

from api.blueprints.bp_auth.routes import bp_auth
from api.blueprints.bp_general.routes import bp_general
from api.blueprints.bp_logs.routes import bp_logs
from api.blueprints.bp_render.routes import bp_render
from api.blueprints.bp_video.routes import bp_video
from api.config.backend_config import (
    BasicServerConfig,
    BasicMongoConfig,
    BasicSecurityConfig,
)
from api.hardware.cam import Camera
from api.log import app_logger
from api.utils.backup import BackUp


class APP:
    """
    Class to create a Flask api with the specified configuration.
    """

    def __init__(self, deploy: bool = True):
        """
        Initialize the class with the specified configuration.
        :param deploy: Flag to indicate if the api is for deploy or testing.
        """
        # Set the deployment flag
        self.deploy = deploy

        # Set a logger
        self.logger = app_logger

        # Config the Backend
        self.flask_app = BasicServerConfig(
            path_to_config=os.path.join(os.getcwd(), "secrets", "backend_config.json")
        )

        # Configure FrontEnd
        self.react_app = BasicServerConfig(
            path_to_config=os.path.join(os.getcwd(), "secrets", "frontend_config.json")
        )
        self.react_app.load_config()

        # Configure MongoDB
        self.mongo_config = BasicMongoConfig(
            path_to_config=os.path.join(os.getcwd(), "secrets")
        )
        self.mongo_config.load_credentials()

        # Set the secret key to enable JWT authentication
        self.security_config = BasicSecurityConfig(
            path_to_secrets=os.path.join(os.getcwd(), "secrets")
        )

        # Create a backup
        self.backup = BackUp(self.mongo_config)

        # Start the camera
        self.camera = Camera()
        self.camera.run_digicam()

    def create_app(self) -> Flask:
        """
        Create a Flask api with the specified configuration.
        :return: A Flask api.
        """
        # Initialize Flask
        app = Flask(__name__)

        # Config the api for deploy or testing
        if self.deploy:
            app.config.from_object(None)
        else:
            from config.backend_config import TestConfig

            app.config.from_object(TestConfig)

        # Register the blueprints
        app.register_blueprint(bp_general)
        app.register_blueprint(bp_logs)
        app.register_blueprint(bp_auth)
        app.register_blueprint(bp_render)
        app.register_blueprint(bp_video)

        # Initialize MongoDB
        app.config["MONGODB_SETTINGS"] = self.mongo_config.model_dump()
        mongo = MongoEngine()
        mongo.init_app(app)

        # Initialize JWT
        app.config["JWT_SECRET_KEY"] = self.security_config.secret
        jwt = JWTManager(app)

        # Enable CORS for all routes
        CORS(
            app,
            resources={
                r"/*": {"origins": f"{self.react_app.host}:{self.react_app.port}"}
            },
        )

        # Check the server status
        self.logger.info("*** Starting the backend ***")
        self.logger.info("--- Checking the server status ---")
        self.logger.info(
            f"MongoDB: http://{self.mongo_config.host}:{self.mongo_config.port}"
            f' - Status: {"UP" if self.mongo_config.server_is_up() else "DOWN"}'
        )
        self.logger.info(
            f'UI: {self.react_app.host}:{self.react_app.port} - '
            f'Status: {"UP" if self.react_app.server_is_up() else "DOWN"}'
        )

        return app

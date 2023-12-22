import os
import subprocess
import time

import psutil

from api.config.backend_config import BasicCameraConfig
from api.log import app_logger
from api.responses.basic_responses import BasicResponse, DataResponse
from api.utils.files import check_for_new_files


class Camera:
    """
    Python interface for the open source digicam-control software. Initialize the program by specifying where
    digiCamControl is installed. If left empty, the default location (C:/Program Files (x86)/digiCamControl) will be
    assumed. If openProgram is set to true, digiCamControl will automatically be opened in the background.
    """

    def __init__(self, cam_config: BasicCameraConfig = None):
        """
        Initialize the program by specifying where digiCamControl is installed. If left empty, use the default location
        @:param config: Configuration of the camera as a BasicCameraConfig object.
        """
        if cam_config is None:
            cam_config = BasicCameraConfig(
                path_to_config=os.path.join(
                    os.getcwd(), "secrets", "camera_config.json"
                )
            )
            cam_config.load_config(logger=app_logger)

        self.config: BasicCameraConfig = cam_config
        self.exeDir: str = cam_config.controller_path
        self.is_up: bool = False

        # Commands
        self.capture_command: str = "Capture"
        self.liveview_show_command: str = "do LiveViewWnd_Show"
        self.liveview_hide_command: str = "do LiveViewWnd_Hide"
        self.liveview_start_command: str = "do StartRecord"
        self.liveview_stop_command: str = "do StopRecord"

        # Check if the program is installed and running
        exec_response: BasicResponse = self.run_digicam()
        self.is_up: bool = exec_response.success

        # Camera name
        self.is_plug: bool = self.is_camera()

    def is_running(self) -> bool:
        """
        Check if the program is running.
        :return: Boolean indicating if the program is running.
        """
        try:
            if not ("CameraControl.exe" in (i.name() for i in psutil.process_iter())):
                cam_response = self.open_program()
                if not cam_response.success:
                    app_logger.error(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                    return False
                else:
                    app_logger.info(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                    # time.sleep(10)
                    return True
            else:
                return True
        except Exception as e:
            app_logger.error(f"digiCamControl: @{self.exeDir} - Status: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Check if the camera is connected using the OpenCv library.
        """
        # TODO: Implement this method

    def run_digicam(self) -> BasicResponse:
        """
        Run the digiCamControl program.
        :return: BasicResponse indicating the success of the operation with a message.
        """
        # Run the program
        if os.path.exists(self.exeDir + r"/CameraControlRemoteCmd.exe"):
            # Check if the program is already running
            if not ("CameraControl.exe" in (i.name() for i in psutil.process_iter())):
                cam_response = self.open_program()
                if not cam_response.success:
                    app_logger.error(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                else:
                    app_logger.info(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                    time.sleep(10)
            else:
                cam_response = BasicResponse(
                    success=True,
                    status_code=200,
                    message="CameraControl.exe is running",
                )
        else:
            app_logger.error(f"digiCamControl: @{self.exeDir} - Status: Not installed")
            cam_response = BasicResponse(
                success=False,
                status_code=500,
                message="CameraControl.exe is not installed",
            )
        return cam_response

    def open_program(self) -> BasicResponse:
        """
        Opens the CameraControl.exe application.
        :return:
        """
        try:
            subprocess.Popen(self.exeDir + r"/CameraControl.exe")
            app_logger.info(f"digiCamControl: @{self.exeDir} - Status: UP")
            return BasicResponse(
                success=True,
                status_code=200,
                message="CameraControl.exe is running",
            )
        except Exception as e:
            app_logger.error(f"digiCamControl: @{self.exeDir} - Status: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message="CameraControl.exe is not running",
            )

    def close_program(self) -> BasicResponse:
        """
        Closes the CameraControl.exe application.
        return: BasicResponse indicating the success of the operation with a message.
        """
        try:
            # Check if the program is running
            if "CameraControl.exe" in (i.name() for i in psutil.process_iter()):
                for proc in psutil.process_iter():
                    if proc.name() == "CameraControl.exe":
                        proc.kill()
                app_logger.info(f"digiCamControl: @{self.exeDir} - Status: DOWN")
                return BasicResponse(
                    success=True,
                    status_code=200,
                    message="CameraControl.exe is now not running",
                )
            else:
                app_logger.info(f"digiCamControl: @{self.exeDir} - Status: DOWN")
                return BasicResponse(
                    success=True,
                    status_code=200,
                    message="CameraControl.exe is not running",
                )
        except Exception as e:
            app_logger.error(f"digiCamControl: @{self.exeDir} - Status: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message="CameraControl.exe is not running",
            )

    def config_camera(self, config: BasicCameraConfig) -> BasicResponse:
        """
        Configure the camera with the specified configuration.
        :param config: Configuration of the camera as a BasicCameraConfig object.
        :return: BasicResponse indicating the success of the operation with a message.
        """
        try:
            self.set_iso(config.iso)
            self.set_aperture(config.aperture)
            self.set_exposure_comp(config.exposure_comp)
            self.set_shutterspeed(config.shutter_speed)
            self.set_autofocus(config.autofocus)
            self.set_compression(config.compression)
            self.set_whitebalance(config.white_balance)
            self.set_counter(config.counter)
            self.set_image_name(config.image_name)
            self.set_transfer(config.transfer_mode)
            self.set_folder(config.storage_path)

            # Log the configuration of the camera as a dict
            app_logger.info(f"Camera configuration: {config.model_dump()}")

            return BasicResponse(
                success=True,
                status_code=200,
                message="Camera configuration successful",
            )
        except Exception as e:
            # Log the configuration of the camera as a dict
            app_logger.error(f"Camera configuration failed: {e}")

            return BasicResponse(
                success=False,
                status_code=500,
                message="Camera configuration failed",
            )

    def capture(self, location: str = None) -> BasicResponse:
        """
        Takes a photo - filename and location can be specified in string location, otherwise the default will be used.
        :param location: Location and filename of the image to be saved.
        :return: a DataResponse indicating the success of the operation with a message and the path of the image.
        """
        if location is None:
            image_name = (
                    self.config.image_name + "_" + time.strftime("%Y%m%d_%H%M%S") + ".jpg"
            )
            location = os.path.join(self.config.storage_path, image_name)
        else:
            image_name = os.path.basename(location)

        try:
            cmd = [
                os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                "/c",
                self.capture_command,
                location,
            ]
            response = subprocess.run(cmd, cwd=self.exeDir, capture_output=True)
            if response.returncode == 0:
                app_logger.info(f"Camera: Image capture - Location: {location}")

                # Load the image as bytes and delete the file
                with open(location, "rb") as image:
                    image_bytes = image.read()
                os.remove(location)

                return DataResponse(
                    success=True,
                    data={"image": image_bytes, "image_name": image_name},
                    status_code=200,
                    message=f"Camera: Image capture - Location: {location}",
                )
            else:
                app_logger.error(
                    f"Camera: Image capture failed - Status: {response.returncode}"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: Image capture failed - Status: {response.returncode}",
                )
        except Exception as e:
            app_logger.error(f"Camera: Image capture failed - Error: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message=f"Camera: Image capture failed - Error: {e}",
            )

    def capture_video(
            self, location: str = None, duration: float = 420
    ) -> BasicResponse:
        """
        Takes a video - filename and location can be specified in string location, otherwise the default will be used.
        :param location: Location and filename of the video to be saved.
        :param duration: Duration of the video in seconds. Default = 420
        :return: a DataResponse indicating the success of the operation with a message and the path of the video.
        """
        try:
            self.show_live_view()
            self.run_cmd("do StartRecord")
            time.sleep(duration)
            self.run_cmd("do StopRecord")
            self.run_cmd("do LiveViewWnd_Hide")

            if check_for_new_files(location):
                app_logger.info("Camera: Video recorded successfully")
                return DataResponse(
                    success=True,
                    status_code=200,
                    message=f"Video capture successfully",
                    data={"path": location},
                )
        except (Exception, IOError) as e:
            app_logger.error(f"Camera: Video recording fail: {e}")
            return BasicResponse(
                sucess=True, status_code=200, message=f"Video recording fail: {e}"
            )

    def start_recording(self) -> BasicResponse:
        """
        Start recording a video - filename and location can be specified in string location, otherwise the default will
        be used.
        :return: BasicResponse indicating the success of the operation with a message.
        """
        try:
            # Start the live view window
            time.sleep(5)
            cmd = [
                os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                "/c",
                "do",
                "LiveViewWnd_Show",
            ]
            response_cmd = subprocess.run(cmd, cwd=self.exeDir, capture_output=True)
            response_cmd = str(response_cmd.stdout)
            if "no camera is connected" in response_cmd:
                app_logger.error(
                    f"Camera: Live view start failed - Status: No camera is connected"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Error: No camera is " f"connected",
                )
            elif 'response:""' in response_cmd or "response:null" in response_cmd:
                app_logger.info(f"Camera: Live view started - Status: {response_cmd}")
                # Start recording
                cmd = [
                    os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                    "/c",
                    "do",
                    "StartRecord",
                ]
                response_cmd = subprocess.run(cmd, capture_output=True)
                if 'response:""' in str(response_cmd.stdout):
                    app_logger.info(f"Camera: Recording started")
                    return BasicResponse(
                        success=True,
                        status_code=200,
                        message=f"Camera: Recording started",
                    )
                else:
                    app_logger.error(
                        f"Camera: Recording start failed - Status: {response_cmd.returncode}"
                    )
                    return BasicResponse(
                        success=False,
                        status_code=500,
                        message=f"Camera: Recording failed - Status: {response_cmd}",
                    )
            else:
                app_logger.error(
                    f"Camera: Live view start failed - Status: {response_cmd}"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: LiveViewWnd failed - Status: {response_cmd}",
                )
        except Exception as e:
            app_logger.error(f"Camera: Recording start failed - Error: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message=f"Camera: Recording failed - Error: {e}",
            )

    def stop_recording(self) -> BasicResponse:
        """
        Stop recording a video - filename and location can be specified in string location, otherwise the default will
        be used.
        :return: BasicResponse indicating the success of the operation with a message.
        """
        try:
            # Stop recording
            cmd = [
                os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                "/c",
                "do",
                "StopRecord",
            ]
            response = subprocess.run(cmd, capture_output=True)
            if 'response:""' in str(response.stdout):
                app_logger.info(f"Camera: Recording stopped")

                # Hide the live view window
                cmd = [
                    os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                    "/c",
                    "do",
                    "LiveViewWnd_Hide",
                ]
                subprocess.run(cmd, capture_output=True)
                return BasicResponse(
                    success=True,
                    status_code=200,
                    message=f"Camera: Recording stopped",
                )
            else:
                app_logger.error(
                    f"Camera: Recording stop failed - Status: {response.returncode}"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: Recording stop failed - Status: {response.returncode}",
                )
        except Exception as e:
            app_logger.error(f"Camera: Recording stop failed - Error: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message=f"Camera: Recording stop failed - Error: {e}",
            )

    def set_folder(self, folder: str):
        """
        Set the folder where the pictures are saved.
        :param folder: Folder where the pictures are saved.
        :return:
        """
        self.__set_cmd("session.folder", folder)

    def set_image_name(self, name: str):
        """
        Set the name of the images.
        :param name: Prefix of the image name.
        :return:
        """
        self.__set_cmd("session.name", f"{name}_{time.strftime('%Y%m%d_%H%M%S')}")

    def set_counter(self, counter: int = 0):
        """
        Set the counter to a specific number (default = 0).
        :param counter: Integer number to set the counter to. default = 0
        :return:
        """
        self.__set_cmd("session.Counter", str(counter))

    def is_camera(self):
        try:
            # Start the live view window
            time.sleep(5)
            cmd = [
                os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                "/c",
                "list",
                "cameras",
            ]
            response_cmd = subprocess.run(cmd, cwd=self.exeDir, capture_output=True)
            response_cmd = str(response_cmd.stdout)
            if "no camera is connected" in response_cmd or "response:null" in response_cmd:
                return False
            elif '"_??_pcistor"' in response_cmd:
                return False
            elif "EOS" in response_cmd:
                return True
            else:
                return False
        except Exception:
            return False

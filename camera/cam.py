import os
import time
import psutil
import subprocess

from config.backend_config import BasicCameraConfig, logger
from responses.basic_responses import BasicResponse, DataResponse
from utils.files import check_for_new_files


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
            cam_config.load_config()

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
        exec_response = self.run_digicam()
        self.is_up = exec_response.success

    def is_running(self) -> bool:
        """
        Check if the program is running.
        :return: Boolean indicating if the program is running.
        """
        try:
            if not ("CameraControl.exe" in (i.name() for i in psutil.process_iter())):
                cam_response = self.open_program()
                if not cam_response.success:
                    logger.error(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                    return False
                else:
                    logger.info(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                    time.sleep(10)
                    return True
            else:
                return True
        except Exception as e:
            logger.error(f"digiCamControl: @{self.exeDir} - Status: {e}")
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
                    logger.error(
                        f"digiCamControl: @{self.exeDir} - Status: {cam_response.message}"
                    )
                else:
                    logger.info(
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
            logger.error(f"digiCamControl: @{self.exeDir} - Status: Not installed")
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
            logger.info(f"digiCamControl: @{self.exeDir} - Status: UP")
            return BasicResponse(
                success=True,
                status_code=200,
                message="CameraControl.exe is running",
            )
        except Exception as e:
            logger.error(f"digiCamControl: @{self.exeDir} - Status: {e}")
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
            logger.info(f"Camera configuration: {config.model_dump()}")

            return BasicResponse(
                success=True,
                status_code=200,
                message="Camera configuration successful",
            )
        except Exception as e:
            # Log the configuration of the camera as a dict
            logger.error(f"Camera configuration failed: {e}")

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
                logger.info(f"Camera: Image capture - Location: {location}")

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
                logger.error(
                    f"Camera: Image capture failed - Status: {response.returncode}"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: Image capture failed - Status: {response.returncode}",
                )
        except Exception as e:
            logger.error(f"Camera: Image capture failed - Error: {e}")
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
                logger.info("Camera: Video recorded successfully")
                return DataResponse(
                    success=True,
                    status_code=200,
                    message=f"Video capture successfully",
                    data={"path": location},
                )
        except (Exception, IOError) as e:
            logger.error(f"Camera: Video recording fail: {e}")
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
            cmd = [
                os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                "/c",
                "do",
                "LiveViewWnd_Show",
            ]
            response_cmd = subprocess.run(cmd, cwd=self.exeDir, capture_output=True)
            response_cmd = str(response_cmd.stdout)
            if "no camera is connected" in response_cmd:
                logger.error(
                    f"Camera: Live view start failed - Status: No camera is connected"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Error: No camera is " f"connected",
                )
            elif 'response:""' in response_cmd or "response:null" in response_cmd:
                logger.info(f"Camera: Live view started - Status: {response_cmd}")
                # Start recording
                cmd = [
                    os.path.join(self.exeDir, "CameraControlRemoteCmd.exe"),
                    "/c",
                    "do",
                    "StartRecord",
                ]
                response_cmd = subprocess.run(cmd, capture_output=True)
                if 'response:""' in str(response_cmd.stdout):
                    logger.info(f"Camera: Recording started")
                    return BasicResponse(
                        success=True,
                        status_code=200,
                        message=f"Camera: Recording started",
                    )
                else:
                    logger.error(
                        f"Camera: Recording start failed - Status: {response_cmd.returncode}"
                    )
                    return BasicResponse(
                        success=False,
                        status_code=500,
                        message=f"Camera: Recording failed - Status: {response_cmd}",
                    )
            else:
                logger.error(f"Camera: Live view start failed - Status: {response_cmd}")
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: LiveViewWnd failed - Status: {response_cmd}",
                )
        except Exception as e:
            logger.error(f"Camera: Recording start failed - Error: {e}")
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
                logger.info(f"Camera: Recording stopped")

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
                logger.error(
                    f"Camera: Recording stop failed - Status: {response.returncode}"
                )
                return BasicResponse(
                    success=False,
                    status_code=500,
                    message=f"Camera: Recording stop failed - Status: {response.returncode}",
                )
        except Exception as e:
            logger.error(f"Camera: Recording stop failed - Error: {e}")
            return BasicResponse(
                success=False,
                status_code=500,
                message=f"Camera: Recording stop failed - Error: {e}",
            )

    # %% Capture

    # %% Folder
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

    # %% Transfer mode
    def set_transfer(self, location: str = "Save_to_PC_only") -> int:
        """
        Define where the pictures should be saved - "Save_to_camera_only", "Save_to_PC_only" or
        "Save:to_PC_and_camera"
        @:param location: Value to set the transfer mode to. Possible values: "Save_to_camera_only", "Save_to_PC_only"
         or "Save:to_PC_and_camera"
        @:return: Code indicating the success of the operation
        """
        print("The pictures will be saved to %s." % location)
        return self.run_cmd("set transfer %s" % location)

    # %% Autofocus
    def show_live_view(self) -> int:
        print("Showing live view window.")
        return self.run_cmd("do LiveViewWnd_Show")

    def set_autofocus(self, status: bool = True):
        """
        Turn the autofocus on (default) or off.
        :param status: Boolean value to turn the autofocus on or off. Default = True
        :return:
        """
        if status:
            self.capture_command = "Capture"
            print("Autofocus is on.")
        else:
            self.capture_command = "CaptureNoAf"
            print("Autofocus is off.")

    # %% Shutters-peed
    def set_shutterspeed(self, shutter_speed: str) -> int:
        """
        Set the shutter speed
        :param shutter_speed: Set the shutter speed - e.g. "1/50", "1/250" or 1s.
        :return: Value indicating the success of the operation
        """
        return self.__set_cmd("shutterspeed", shutter_speed)

    def get_shutterspeed(self):
        """
        Get the current shutter speed
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("shutterspeed")

    def list_shutterspeed(self):
        """
        Get a list off all possible shutter speeds
        :return: Value indicating the success of the operation
        """
        return self.__list_cmd("shutterspeed")

    # %% ISO
    def set_iso(self, iso: int = 100) -> BasicResponse:
        """
        Set the current ISO value
        :param iso: Current ISO value - e.g. 100, 200 or 400.
        :return: Value indicating the success of the operation
        """
        response = self.__set_cmd("Iso", str(iso))
        if response == 0:
            logger.info(f"Camera: ISO set to {iso}")
            return BasicResponse(
                success=True,
                status_code=200,
                message=f"Camera: ISO set to {iso}",
            )
        else:
            logger.error(f"Camera: ISO set failed - Status: {response}")
            return BasicResponse(
                success=False,
                status_code=500,
                message=f"Camera: ISO set failed - Status: {response}",
            )

    def get_iso(self):
        """
        Get the current ISO Value.
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("Iso")

    def list_iso(self) -> list:
        """
        Get a list off all possible ISO values - e.g. 100, 200 or 400.
        :return: Value indicating the success of the operation
        """
        return self.__list_cmd("Iso")

    # %% Aperture
    def set_aperture(self, aperture: float = 2.8) -> int:
        """
        Set the aperture
        :param aperture: Set the cam aperture - e.g. 2.8 or 8.0.
        :return: Value indicating the success of the operation
        """
        return self.__set_cmd("aperture", str(aperture))

    def get_aperture(self) -> int | str:
        """
        Get the current aperture - e.g. 2.8 or 8.0.
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("aperture")

    def list_aperture(self) -> list:
        """
        Get a list off all possible aperture values - e.g. 2.8 or 8.0.
        :return: Value indicating the success of the operation
        """
        return self.__list_cmd("aperture")

    # %% Exposure Compensation
    def set_exposure_comp(self, ec: str = "0.0") -> int:
        """
        Set the exposure compensation - e.g. "-1.0" or "+2.3"
        :param ec: Current exposure compensation - e.g. "-1.0" or "+2.3"
        :return: Value indicating the success of the operation
        """
        return self.__set_cmd("exposurecompensation", ec)

    def get_exposure_comp(self) -> int | str:
        """
        Get the current exposure compensation - e.g. "-1.0" or "+2.3"
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("exposurecompensation")

    def list_exposure_comp(self) -> list:
        """
        Get a list off all possible exposure compensation values - e.g. "-1.0" or "+2.3"
        :return: List of all possible exposure compensation values - e.g. "-1.0" or "+2.3"
        """
        return self.__list_cmd("exposurecompensation")

    # %% Compression
    def set_compression(self, comp: str = "RAW") -> int:
        """
        Set the compression - e.g. "RAW" or "JPEG (BASIC)"
        :param comp: Current compression. default = "RAW"
        :return: Value indicating the success of the operation
        """
        return self.__set_cmd("compressionsetting", comp)

    def get_compression(self) -> int | str:
        """
        Get the current compression - e.g. "RAW" or "JPEG (BASIC)"
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("compressionsetting")

    def list_compression(self) -> list:
        """
        Get a list off all possible compression setting - e.g. "RAW" or "JPEG (BASIC)"
        :return: Value indicating the success of the operation
        """
        return self.__list_cmd("compressionsetting")

    # %% White balance
    def set_whitebalance(self, wb: str) -> int:
        """
        Set the white balance - e.g. "Auto" or "Daylight" or "Cloudy"
        :param wb: Set the white balance - e.g. "Auto" or "Daylight" or "Cloudy"
        :return: Value indicating the success of the operation
        """
        return self.__set_cmd("whitebalance", wb)

    def get_whitebalance(self) -> int | str:
        """
        Get the current white balance - e.g. "Auto" or "Daylight" or "Cloudy"
        :return: Value indicating the success of the operation
        """
        return self.__get_cmd("whitebalance")

    def list_whitebalance(self) -> list:
        """
        Get a list off all possible white balance values - e.g. "Auto" or "Daylight" or "Cloudy"
        :return: Value indicating the success of the operation
        """
        return self.__list_cmd("whitebalance")

    # %% Commands

    def run_cmd(self, cmd: str) -> int:
        """
        Run a generic command directly with CameraControlRemoteCmd.exe
        :param cmd: Command to run on digiCamControl
        :return: Value indicating the success of the operation
        """
        r = subprocess.check_output(
            "cd %s && CameraControlRemoteCmd.exe /c %s" % (self.exeDir, cmd),
            shell=True,
        ).decode()
        if "null" in r:  # Success
            return 0
        elif r'""' in r:  # Success
            return 0
        else:  # Error
            print("Error: %s" % r)  # Format output message
            return -1

    def __set_cmd(self, cmd: str, value: str) -> int:
        """
        Run a set command with CameraControlRemoteCmd.exe
        :param cmd: Command to run on digiCamControl
        :param value: Value to set the command to
        :return: Value indicating the success of the operation
        """
        r = subprocess.check_output(
            "cd %s && CameraControlRemoteCmd.exe /c set %s"
            % (self.exeDir, cmd + " " + value),
            shell=True,
        ).decode()
        if "null" in r:  # Success
            print("Set the %s to %s" % (cmd, value))
            return 0
        else:  # Error
            print("Error: %s" % r[109:])  # Format output message
            return -1

    def __get_cmd(self, cmd: str) -> int | str:
        """
        Run a get command with CameraControlRemoteCmd.exe
        :param cmd: Command to run on digiCamControl
        :return: Value indicating the success of the operation
        """
        r = subprocess.check_output(
            "cd %s && CameraControlRemoteCmd.exe /c get %s" % (self.exeDir, cmd),
            shell=True,
        ).decode()
        if "Unknown parameter" in r:  # Error
            print("Error: %s" % r[109:])  # Format output message
            return -1
        else:  # Success
            return_value = r[96:-6]
            print("Current %s: %s" % (cmd, return_value))  # Format output message
            return return_value

    def __list_cmd(self, cmd: str) -> int | list[str]:
        """
        Run a list command with CameraControlRemoteCmd.exe
        :param cmd: Command to run on digiCamControl
        :return: Value indicating the success of the operation
        """
        r = subprocess.check_output(
            "cd %s && CameraControlRemoteCmd.exe /c list %s" % (self.exeDir, cmd),
            shell=True,
        ).decode()
        if "Unknown parameter" in r:  # Error
            print("Error: %s" % r[109:])  # Format output message
            return -1
        else:  # Success
            return_list = r[96:-6].split(",")  # Format response and turn into a list
            return_list = [e[1:-1] for e in return_list]  # Remove "" from string
            print(
                "List of all possible %ss: %s" % (cmd, return_list)
            )  # Format output message
            return return_list

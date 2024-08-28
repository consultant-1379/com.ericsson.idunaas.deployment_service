"""This module contains a class and functions relating to the deployment manager working directory."""

import logging
from pathlib import Path
from aws_deployment_manager import errors
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class Workdir:
    """This class represents the working directory for the deployment manager."""

    def __init__(self):
        """The constructor."""
        self.workdir_path = constants.WORKDIR_PATH
        workdir_path_object = Path(self.workdir_path)
        if not workdir_path_object.exists():
            raise errors.WorkdirNotMountedError("Please mount a working directory into the {0} "
                                                "path using -v <local_working_directory>:{0}"
                                                .format(workdir_path_object)
                                                )

        if not workdir_path_object.is_dir():
            raise errors.WorkdirNotADirectoryError("The working directory that you have mounted is not a directory, "
                                                   "please mount a valid working directory.")

        self.config_file_path = constants.CONFIG_FILE_PATH
        self.logs_subdirectory = constants.LOGS_DIRECTORY_NAME
        self.logs_directory = constants.LOGS_DIRECTORY_PATH

    def init(self):
        """Initialize the working directory."""
        self.__create_directory_structure()

    def get_workdir_path(self):
        """
        Get Workdir Path
        :return: Workdir Path
        """
        return self.workdir_path

    def __create_directory_structure(self):
        """Create the directory structure of the working directory."""
        Path(self.logs_directory).mkdir(parents=True, exist_ok=True)

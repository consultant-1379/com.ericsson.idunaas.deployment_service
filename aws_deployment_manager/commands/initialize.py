"""
This module implements Init command
"""
import logging
import os
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class InitManager():
    """ Main Class for Init command """
    def __init__(self):
        self.__stage_log_path = constants.INSTALL_STAGE_LOG_PATH
        self.__workdir_path = constants.WORKDIR_PATH

    def init(self):
        """
        Initialize IDUN for new install
        """
        LOG.info("Initializing IDUN Deployment Manager...")

        if os.path.exists(self.__stage_log_path):
            os.remove(self.__stage_log_path)

        LOG.info("Initialized IDUN Deployment Manager...")

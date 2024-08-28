"""
This module implements Prepare command
"""
import logging
import os
import shutil
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class PrepareManager():
    """ Main Class for Prepare command """
    def __init__(self, override):
        self.__override = override
        self.__output_path = constants.CONFIG_FILE_PATH
        self.__config_template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_CONFIG_FILE)

    def prepare_config_file(self):
        """
        Generate IDUN Config Template File
        :return: Path of config temnplate file
        """
        LOG.info("Checking if a config file already exists at {0}".format(self.__output_path))
        if os.path.exists(self.__output_path):
            if not self.__override:
                msg = "Config file already exists at {0}. Please take backup and rename the file and try again"\
                    .format(self.__output_path)
                LOG.error(msg)
                raise Exception(msg)

            LOG.warning("Config file {} already exist and will be overwritten".format(self.__output_path))

        # Copy template file to output file
        LOG.info("Generating IDUN config template file at {0}".format(self.__output_path))
        shutil.copy2(src=self.__config_template_path, dst=self.__output_path)
        return self.__output_path

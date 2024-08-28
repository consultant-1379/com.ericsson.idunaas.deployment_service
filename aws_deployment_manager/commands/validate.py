"""
This module implements Validate Command
"""
import logging
from aws_deployment_manager import utils, constants

LOG = logging.getLogger(__name__)


class ValidateManager:
    """ Main Class for Validate Command """
    def __init__(self):
        self.__config = utils.load_yaml(file_path=constants.CONFIG_FILE_PATH)
        LOG.info(self.__config)

    def validate_config(self):
        """
        Validate the IDUN Configuration File
        """
        LOG.info("Starting Config Validation...")
        configuration_valid, validation_errors = utils.validate_idun_config(config=self.__config)

        LOG.info("================================================================================================")
        if not configuration_valid:
            LOG.error("Configuration File not valid. {0} errors found".format(len(validation_errors)))
            for error in validation_errors:
                LOG.error(error)
        else:
            LOG.info("Configuration File valid. 0 errors found")
        LOG.info("================================================================================================")

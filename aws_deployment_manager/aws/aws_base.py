"""
This is the base class for AWS Clients
"""
import logging
from botocore.config import Config
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class AwsBase:
    """
    Base Class for AWS Clients
    """
    def __init__(self, config):
        """
        Init Method
        :param config: IDUN COnfiguration Parameters
        """
        self.__config = config
        self.__aws_region = self.__config[constants.AWS_REGION]

        self.__aws_client_config = Config(
            region_name = self.__aws_region,
            retries = {
                'max_attempts': 5,
                'mode': 'standard'
            }
        )

    def get_aws_client_config(self):
        """
        Get AWS Client Config
        :return: AWS Client Config
        """
        return self.__aws_client_config

    def get_aws_region(self):
        """
        Get AWS Region
        :return:
        """
        return self.__aws_region

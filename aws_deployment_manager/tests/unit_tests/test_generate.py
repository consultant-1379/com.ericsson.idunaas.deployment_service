"""
Unit Tests for the generate module.
"""

import random
import shutil
import string
import tempfile

import boto3
import pytest

from aws_deployment_manager import constants
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.generate import GenerateManager
from aws_deployment_manager.commands.install import InstallManager


VALID_CONFIG_FILE_PATH = "/workdir/config.yaml"

VALID_REGION = 'eu-west-1'


# pylint: disable=no-self-use, protected-access, unused-argument, unused-variable, trailing-whitespace, trailing-newlines
@pytest.mark.usefixtures("setup_config_file")
class TestInstall:
    """
    Class to run tests for the generate module.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, shared_data):
        """
        Sets up config for running tests and cleans up after the tests are done.
        :param shared_data: test fixture with SharedData object
        """
        yield
        delete = DeleteManager(shared_data.infra_master_stack_name, VALID_REGION)
        delete._delete_cf_stack(delete.infra_master_stack_name)
        delete._delete_templates_bucket()
        constants.CONFIG_FILE_PATH = VALID_CONFIG_FILE_PATH
        shutil.rmtree(shared_data.test_dir)

    @pytest.fixture(scope="class")
    def shared_data(self, setup_config_file):
        """
        Creates a shared data dictionary that can be used my multiple tests.
        :return shared_data: a shared data object
        :rtype: SharedData
        """

        # pylint: disable=too-few-public-methods
        class SharedData:
            """
            Class that holds data that is to be shared across multiple tests.
            """

            def __init__(self):
                self.install_manager = InstallManager('user', 'password')
                self.cloudformation_client = boto3.client('cloudformation')
                self.install_manager.upload_templates()
                self.update_template_urls()
                self.install_manager.s3_url = \
                    'http://localhost:4566/idun-2-deployment-templates/0.1.0'
                self.test_dir = tempfile.mkdtemp()
                self.valid_config_file_path = self.test_dir + "/config.yaml"
                constants.CONFIG_FILE_PATH = self.valid_config_file_path
                letters = string.ascii_lowercase
                random_string = ''.join(random.choice(letters) for i in range(10))
                self.infra_master_stack_name = self.install_manager.infra_master_stack_name + random_string
                self.install_manager.infra_master_stack_name = self.infra_master_stack_name
                self.install_manager.create_or_update_idun_stack()
                self.generate_manager = GenerateManager(self.infra_master_stack_name, VALID_REGION)

            def update_template_urls(self):
                """
                Updates template URLs to point to Localstack instead of S3
                """
                for yaml_file in self.install_manager.template_urls:
                    template_url = self.install_manager.template_urls[yaml_file]
                    self.install_manager.template_urls[yaml_file] = template_url.replace(
                        'https://idun-2-deployment-templates.s3.amazonaws.com',
                        'http://localhost:4566/idun-2-deployment-templates'
                    )

        return SharedData()

    @staticmethod
    def helper_get_expected_docker_config_file_contents():
        """
        Gets expected docker config from the original config file.
        The file contents must be re-worked in the following ways to work with tests:
        - Any empty lines must be removed
        :return expected_docker_config_file_contents: contents of IDUn config file
        :rtype: String
        """
        expected_docker_config_file_contents = open(VALID_CONFIG_FILE_PATH).read()

        return expected_docker_config_file_contents.strip()

    # def test_generate_config_file(self, shared_data):
    #     """
    #     Tests that we can generate the config file correctly
    #     :param shared_data: test fixture with SharedData object
    #     """
    #     shared_data.generate_manager.generate_config_file()
    #     actual_docker_config_file_contents = open(shared_data.valid_config_file_path).read().strip()
    #     expected_docker_config_file_contents = \
    #         self.helper_get_expected_docker_config_file_contents()
    #     assert actual_docker_config_file_contents == expected_docker_config_file_contents
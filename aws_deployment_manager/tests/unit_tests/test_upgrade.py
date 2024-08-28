"""
Unit tests for the upgrade command.
"""

import pytest

from aws_deployment_manager import constants
from aws_deployment_manager.commands.install import InstallManager
from aws_deployment_manager.commands.upgrade import UpgradeManager


# pylint: disable=no-self-use
@pytest.mark.usefixtures("setup_config_file")
class TestUpgrade:
    """
    Class to run tests for the upgrade module.
    """

    @pytest.fixture(scope="class")
    def shared_data(self, setup_config_file):
        """
        Returns a shared object containing the fixtures required for testing.
        :param setup_config_file: config file as setup in conftest.py
        :return shared_data: SharedData object
        :rtype: SharedData
        """
        # pylint: disable=too-few-public-methods
        class SharedData:
            """
            Class to hold the shared data.
            """
            def __init__(self):
                """
                Initialize the shared data.
                """
                self.install_manager = InstallManager('user', 'password')
                self.prepare_templates()
                self.install_manager.create_or_update_idun_stack()
                self.upgrade_manager = UpgradeManager()
                self.upgrade_manager.outputs[constants.EKS_CLUSTER_OIDC] = constants.DUMMY_REPLACEMENT

            def prepare_templates(self):
                """
                Helper method to prepare the CloudFormation templates.
                """
                self.install_manager.upload_templates()
                for yaml_file in self.install_manager.template_urls:
                    template_url = self.install_manager.template_urls[yaml_file]
                    self.install_manager.template_urls[yaml_file] = template_url.replace(
                        'https://idun-2-deployment-templates.s3.amazonaws.com',
                        'http://localhost:4566/idun-2-deployment-templates'
                    )
                self.install_manager.s3_url = \
                    'http://localhost:4566/idun-2-deployment-templates/0.1.0'

        return SharedData()

    def test_upgrade_idun_stack(self, shared_data):
        """
        Creates an IDUN stack and tests that we can update that stack successfully.
        :param shared_data: test fixture with SharedData object
        """
        upgrade_status = shared_data.upgrade_manager.create_or_update_idun_stack()
        assert upgrade_status['ResponseMetadata']['HTTPStatusCode'] == 200

    def test_upgrade_alb_stack_when_not_already_exist(self, shared_data):
        """
        Creates an IDUN stack and tests that we can update that stack successfully.
        :param shared_data: test fixture with SharedData object
        """
        upgrade_status = shared_data.upgrade_manager.create_or_update_alb_controller_stack()
        assert upgrade_status['ResponseMetadata']['HTTPStatusCode'] == 200

    def test_upgrade_alb_stack(self, shared_data):
        """
        Creates an IDUN stack and tests that we can update that stack successfully.
        :param shared_data: test fixture with SharedData object
        """
        upgrade_status = shared_data.upgrade_manager.create_or_update_alb_controller_stack()
        assert upgrade_status['ResponseMetadata']['HTTPStatusCode'] == 200

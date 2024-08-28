"""
Unit tests for the delete command
"""

import pytest
import logging

from aws_deployment_manager import constants
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.install import InstallManager

INVALID_ENV = 'invalid-idun-env'
INVALID_REGION = 'invalid-idun-region'
VALID_REGION = 'eu-west-1'


LOG = logging.getLogger(__name__)

# pylint: disable=no-self-use, protected-access, unused-argument, unused-variable, trailing-whitespace, trailing-newlines
@pytest.mark.usefixtures("setup_config_file")
class TestDelete:
    """
    Class to run tests for the delete module
    """

    @pytest.fixture(scope="class")
    def shared_data(self, setup_config_file):
        """
        Returns a shared object containing the fixtures required for testing
        :param setup_config_file: config file as setup in conftest.py
        :return shared_data: SharedData object
        :rtype: SharedData
        """
        class SharedData:
            """
            Class to hold the shared data
            """
            def __init__(self):
                """
                Initialize the shared data
                """
                self.install_manager = InstallManager('user', 'password')
                self.install_manager.outputs[constants.EKS_CLUSTER_OIDC] = constants.DUMMY_REPLACEMENT
                self.prepare_templates()
                self.install_manager.create_or_update_idun_stack()
                self.install_manager.create_or_update_alb_controller_stack()
                self.delete_manager = DeleteManager(self.install_manager.infra_master_stack_name, VALID_REGION)
                self.delete_manager_invalid_env = DeleteManager(INVALID_ENV, INVALID_REGION)

            def prepare_templates(self):
                """
                Helper method to prepare the CloudFormation templates
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

    def test_delete_alb_stack(self, shared_data):
        """
        Creates an ALB Controller stack and tests that we can delete that stack successfully
        :param shared_data: test fixture with SharedData object
        """
        stack_name = shared_data.delete_manager.alb_controller_stack_name
        deletion_status = shared_data.delete_manager._delete_cf_stack(stack_name)
        if deletion_status is not True:
            LOG.error("stack name = {}".format(stack_name))
            LOG.error("idun stack name = {}".format(shared_data.delete_manager.infra_master_stack_name))
            LOG.error("stacks = {}".format(shared_data.delete_manager.get_aws_cfclient().list_stacks()))
        assert deletion_status is True

    def test_delete_idun_stack(self, shared_data):
        """
        Creates an IDUN stack and tests that we can delete that stack successfully
        :param shared_data: test fixture with SharedData object
        """

        delete = shared_data.delete_manager
        deletion_status = delete._delete_cf_stack(delete.infra_master_stack_name)
        assert deletion_status is True

    def test_delete_idun_stack_invalid_env(self, shared_data):
        """
        Tests that the logic downstream of the delete command returns the appropriate
        response (None)  when we attempt to delete a stack which doesn't exist
        :param shared_data: test fixture with SharedData object
        """

        delete = shared_data.delete_manager_invalid_env
        deletion_status = delete._delete_cf_stack(delete.infra_master_stack_name)
        assert deletion_status is False


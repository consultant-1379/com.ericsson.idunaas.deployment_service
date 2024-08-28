"""
Unit Tests for the install module.
"""
import string
import random

import boto3
import pytest

from aws_deployment_manager import constants
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.install import InstallManager


# pylint: disable=no-self-use, protected-access, unused-argument, unused-variable, trailing-whitespace, trailing-newlines
@pytest.mark.usefixtures("setup_config_file")
class TestInstall:
    """
    Class to run tests for the install module.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, shared_data):
        """
        Sets up config for running tests and cleans up after the tests are done.
        :param shared_data: test fixture with SharedData object
        """
        yield
        delete = DeleteManager('idun-2', 'eu-west-1')
        delete._delete_cf_stack(delete.infra_master_stack_name)
        delete._delete_cf_stack(delete.alb_controller_stack_name)
        delete._delete_templates_bucket()
        delete._delete_security_group_from_endpoint()
        shared_data.cloudformation_client.delete_stack(StackName=shared_data.base_vpc_name)

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
                letters = string.ascii_lowercase
                random_string = ''.join(random.choice(letters) for i in range(10))
                self.base_vpc_name = 'idun-base-vpc' + random_string
                constants.BASE_VPC_STACK_NAME = self.base_vpc_name
                self.install_manager = InstallManager('user', 'password')
                self.install_manager.outputs[constants.EKS_CLUSTER_OIDC] = constants.DUMMY_REPLACEMENT
                self.install_manager.upload_templates()
                for yaml_file in self.install_manager.template_urls:
                    template_url = self.install_manager.template_urls[yaml_file]
                    self.install_manager.template_urls[yaml_file] = template_url.replace(
                        'https://idun-2-deployment-templates.s3.amazonaws.com',
                        'http://localhost:4566/idun-2-deployment-templates'
                    )
                self.ec2_client = boto3.client('ec2')
                self.cloudformation_client = boto3.client('cloudformation')

        return SharedData()

    def test_create_base_vpc_stack(self, shared_data):
        """
        Tests that we are able to create the base VPC stack.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.install_manager._create_base_vpc_stack()
        stacks = response['Stacks']
        assert len(stacks) == 1
        base_vpc_stack = stacks[0]
        assert base_vpc_stack['StackName'] == shared_data.base_vpc_name
        assert base_vpc_stack['StackStatus'] == 'CREATE_COMPLETE'

    def test_update_base_vpc_stack(self, shared_data):
        """
        Tests that we are able to update the base VPC stack.
        Then it deletes the test stack.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.install_manager._create_base_vpc_stack()
        stacks = response['Stacks']
        assert len(stacks) == 1
        base_vpc_stack = stacks[0]
        assert base_vpc_stack['StackName'] == shared_data.base_vpc_name
        assert base_vpc_stack['StackStatus'] == 'UPDATE_COMPLETE'

    def test_update_endpoint_security_group(self, shared_data):
        """
        Tests that we are able to add Secondary VPC CIDR to AWS Endpoint Security Group.
        Then we query EC2 to get all security groups and make sure the security group we just
        created is present.
        :param shared_data: test fixture with SharedData object
        """
        vpc_stack_outputs = shared_data.install_manager.get_cf_stack_outputs(constants.BASE_VPC_STACK_NAME)
        shared_data.install_manager._update_endpoint_security_group()

        security_groups = shared_data.ec2_client.describe_security_groups()
        actual_security_group = None
        for security_group in security_groups['SecurityGroups']:
            group_id = security_group['GroupId']
            if group_id == str(
                    vpc_stack_outputs[constants.ENDPOINT_SECURITY_GROUP_ID]):
                actual_security_group = security_group
        assert actual_security_group is not None

    def test_create_idun_stack_(self, shared_data):
        """
        Tests that we are able to create the IDUN stack.
        :param shared_data: test fixture with SharedData object
        """
        shared_data.install_manager.s3_url = \
            'http://localhost:4566/idun-2-deployment-templates/0.1.0'
        response = shared_data.install_manager.create_or_update_idun_stack()
        created_stack_information = response['Stacks'][0]
        assert created_stack_information['StackName'] == 'idun-2'
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def test_create_alb_controller_stack_(self, shared_data):
        """
        Tests that we are able to create the IDUN stack.
        :param shared_data: test fixture with SharedData object
        """
        shared_data.install_manager.s3_url = \
            'http://localhost:4566/idun-2-deployment-templates/0.1.0'
        response = shared_data.install_manager.create_or_update_alb_controller_stack()
        created_stack_information = response['Stacks'][0]
        assert created_stack_information['StackName'] == 'idun-2-alb-controller'
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200


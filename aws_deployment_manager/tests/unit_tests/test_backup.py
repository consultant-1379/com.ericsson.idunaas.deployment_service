"""
Unit Tests for the backup module.
"""

import random
import string
import boto3
import pytest

from aws_deployment_manager import constants
from aws_deployment_manager.commands.backup import BackupManager
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.install import InstallManager

VALID_CONFIG_FILE_PATH = "/workdir/config.yaml"
VALID_REGION = 'eu-west-1'


# pylint: disable=no-self-use
@pytest.mark.usefixtures("setup_config_file")
class TestBackup:
    """
    Class to run tests for the backup module.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, shared_data):
        """
        Sets up config for running tests and cleans up after the tests are done.
        :param shared_data: test fixture with SharedData object
        """
        ec2_client = boto3.client('ec2')
        ec2_resource = boto3.resource('ec2')
        ec2_client.create_key_pair(KeyName='test-idun-keypair')

        yield
        instances = ec2_resource.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        ids = []
        for instance in instances:
            ids.append(instance.id)
        ec2_resource.instances.filter(InstanceIds=ids).terminate()
        ec2_client.delete_key_pair(KeyName='test-idun-keypair')
        delete = DeleteManager('idun-2', 'eu-west-1')
        delete._delete_templates_bucket()
        delete._delete_security_group_from_endpoint()
        shared_data.cloudformation_client.delete_stack(StackName=shared_data.base_vpc_name)

    @pytest.fixture(scope="class")
    def shared_data(self):
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
                self.install_manager.upload_templates()
                for yaml_file in self.install_manager.template_urls:
                    template_url = self.install_manager.template_urls[yaml_file]
                    self.install_manager.template_urls[yaml_file] = template_url.replace(
                        'https://idun-2-deployment-templates.s3.amazonaws.com',
                        'http://localhost:4566/idun-2-deployment-templates'
                    )

                self.install_manager._create_base_vpc_stack()
                self.ec2_client = boto3.client('ec2')
                self.cloudformation_client = boto3.client('cloudformation')
                self.backup_manager = BackupManager()
        return SharedData()

    def test_create_ec2(self, shared_data):
        """
        Tests that we can create ec2 instance correctly
        :param shared_data: test fixture with SharedData object
        """

        shared_data.backup_manager.backup_configure()
        ec2_resource = boto3.resource('ec2')
        instances = ec2_resource.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for instance in instances:
            actual_instance_name = instance.tags[0]['Value']
        assert actual_instance_name == "Backup Server"

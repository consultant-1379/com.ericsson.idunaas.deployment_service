"""
Unit Tests for the base module.
"""
import shutil
import tempfile

import boto3
import pytest

from aws_deployment_manager.commands.base import Base

VALID_LOGS_FILE_CONTENTS = '''
install::finished
upgrade::started
'''

EXPECTED_ALL_STAGES = {
    'install': 'finished',
    'upgrade': 'started'
}

SSO_CONSUMER_ADMIN_ROLE_NAME = 'AWSReservedSSO_SSO-Consumer-admin'


# pylint: disable=no-self-use
@pytest.mark.usefixtures("setup_config_file")
class TestBase:
    """
    Class to run tests for the base module.
    """
    test_dir = tempfile.mkdtemp()
    logs_file_path = test_dir + '/logs.txt'

    @pytest.fixture(scope="class")
    def shared_data(self, setup_config_file):
        """
        Creates a shared data object that can be used my multiple tests.
        :return shared_data: a shared data object
        :rtype: SharedData
        """

        # pylint: disable=too-few-public-methods
        class SharedData:
            """
            Class that holds data that is to be shared across multiple tests.
            """

            def __init__(self):
                self.base = Base()
                self.s3_client = boto3.client('s3')
                self.ec2_client = boto3.client('ec2')
                self.iam_client = boto3.client('iam')
                self.expected_idun_config = {}
                self.expected_base_vpc_config = {}
                self.setup_expected_test_data()

            def setup_expected_test_data(self):
                """
                Sets up the expected configuration variables by querying localstack for the
                information.
                """
                vpcs = self.ec2_client.describe_vpcs()
                vpc_id = vpcs['Vpcs'][0]['VpcId']
                primary_vpc_cidr = vpcs['Vpcs'][0]['CidrBlock']
                subnets = self.ec2_client.describe_subnets()
                subnets_list = subnets['Subnets']
                route_tables = self.ec2_client.describe_route_tables()
                route_table_id = route_tables['RouteTables'][0]['RouteTableId']
                secondary_vpc_cidr = subnets_list[0]['CidrBlock']

                self.expected_idun_config = {
                    'VPCID': vpc_id,
                    'NumPrivateSubnets': '1',
                    'PrivateSubnet01Id': subnets_list[1]['SubnetId'],
                    'PrivateSubnet01Az': 'eu-west-1b',
                    'PrivateSubnet02Id': 'NA',
                    'PrivateSubnet02Az': 'NA',
                    'ControlPlaneSubnetIds': f'{subnets_list[1]["SubnetId"]},'
                                             f'{subnets_list[2]["SubnetId"]}',
                    'EnvironmentName': 'idun-2',
                    'PrimaryVpcCIDR': primary_vpc_cidr,
                    'SecondaryVpcCIDR': secondary_vpc_cidr,
                    'DisablePublicAccess': 'True',
                    'S3URL': 'https://idun-2-deployment-templates.s3-eu-west-1.amazonaws.com/0.1.0',
                    'NodeInstanceType': 'm5.2xlarge',
                    'DiskSize': '20',
                    'MinNodes': '8',
                    'MaxNodes': '10',
                    'SshKeyPairName': 'test-idun-keypair',
                    'PrivateDomainName': 'idunaas.ericsson.se',
                    'K8SVersion': '1.24',
                    'KubeDownscaler': 'True',
                    'AWSRegion': 'eu-west-1',
                    'BackupInstanceType': 't3.medium',
                    'BackupAmiId': 'ami00a40405a13c972f4',
                    'BackupDisk': '50',
                    'BackupPass': 'pass',
                    'Hostnames': "{'so': 'so.eo.idunaas.ericsson.se', "
                                 "'pf': 'pf.eo.idunaas.ericsson.se', "
                                 "'iam': 'iam.eo.idunaas.ericsson.se', "
                                 "'uds': 'uds.eo.idunaas.ericsson.se'}"
                }

                self.expected_base_vpc_config = {
                    'VPCID': vpc_id,
                    'PrivateSubnet01Id': subnets_list[1]["SubnetId"],
                    'PrivateSubnet02Id': subnets_list[2]["SubnetId"],
                    'PrivateRouteTable01': route_table_id,
                    'PrivateRouteTable02': route_table_id,
                    'EnvironmentName': 'idun-2',
                    'PrimaryVpcCIDR': primary_vpc_cidr
                }

        return SharedData()

    def setup_logs_file(self):
        """
        Creates a valid logs file for running tests.
        """
        with open(self.logs_file_path, 'w') as file:
            file.writelines(VALID_LOGS_FILE_CONTENTS)

    @staticmethod
    def setup_test_role(role_name, iam_client):
        """
        Creates a valid IAM role for tests.
        """
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument='{}',
            Description='A test Role'
        )

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, shared_data):
        """
        Sets up config for running tests and cleans up after the tests are done.
        :param shared_data: test fixture with SharedData object
        """
        self.setup_logs_file()
        yield
        shutil.rmtree(self.test_dir)
        shared_data.iam_client.delete_role(
            RoleName=SSO_CONSUMER_ADMIN_ROLE_NAME
        )

    def test_load_stage_states(self, shared_data):
        """
        Tests that we can load stage states from a logs file and that if the log file does not exist
        we return an empty dictionary
        :param shared_data: test fixture with SharedData object
        """
        shared_data.base.load_stage_states('this_log_file_path_does_not_exist.txt')
        assert shared_data.base.all_stages == {}
        shared_data.base.load_stage_states(self.logs_file_path)
        assert shared_data.base.all_stages == EXPECTED_ALL_STAGES

    def test_upload_templates(self, shared_data):
        """
        Tests that we can upload template files to S3 and assert that the bucket with template files
        is present in S3
        :param shared_data: test fixture with SharedData object
        """
        shared_data.base.upload_templates()
        expected_bucket_name = shared_data.base.bucket_name
        buckets_response = shared_data.s3_client.list_buckets()
        all_buckets = buckets_response['Buckets']
        contents_response = shared_data.s3_client\
            .list_objects_v2(Bucket='idun-2-deployment-templates')
        bucket_contents = contents_response['Contents']
        assert any([expected_bucket_name == bucket['Name'] for bucket in all_buckets])
        assert len(bucket_contents) > 0

    def test_get_config_parameters(self, shared_data):
        """
        Tests that the IDUN config we get is in the expected format and has the right content
        :param shared_data: test fixture with SharedData object
        """
        expected_idun_config_test = shared_data.expected_idun_config
        for k in list(expected_idun_config_test.keys()):
            if k.startswith('Backup'):
                del expected_idun_config_test[k]
        actual_config = shared_data.base.get_config_parameters_for_idun_cf_stack()
        assert actual_config == expected_idun_config_test

    def test_get_base_vpc_config_parameters(self, shared_data):
        """
        Tests that the base VPC config we get is in the expected format and has the right content
        :param shared_data: test fixture with SharedData object
        """
        actual_base_vpc_config = shared_data.base.get_base_vpc_config_parameters()
        assert actual_base_vpc_config == shared_data.expected_base_vpc_config

    def test_stage_executed(self, shared_data):
        """
        Tests that we correctly check if a stage was executed (has finished) or not
        :param shared_data: test fixture with SharedData object
        """
        install_has_finished = shared_data.base.stage_executed('install')
        upgrade_has_finished = shared_data.base.stage_executed('upgrade')

        assert install_has_finished is True
        assert upgrade_has_finished is False

    def test_update_stage_state(self, shared_data):
        """
        Tests that we can correctly update the upgrade stage to finished
        :param shared_data: test fixture with SharedData object
        """
        shared_data.base.update_stage_state('upgrade', 'finished')
        shared_data.base.load_stage_states(self.logs_file_path)
        upgrade_has_finished = shared_data.base.stage_executed('upgrade')
        assert upgrade_has_finished is True

    def test_execute_stage(self, shared_data):
        """
        Tests that we can execute a stage, call the function and update the log file correctly
        :param shared_data: test fixture with SharedData object
        """
        function_executed = False

        def mock_function():
            nonlocal function_executed
            function_executed = True

        shared_data.base.execute_stage(mock_function, 'create')
        shared_data.base.load_stage_states(self.logs_file_path)
        create_has_finished = shared_data.base.stage_executed('create')
        assert function_executed is True
        assert create_has_finished is True

    def test_execute_stage_skip(self, shared_data):
        """
        Tests that we if we call a stage that has already finished, we don't execute it again
        :param shared_data: test fixture with SharedData object
        """
        function_executed = False

        def mock_function_that_should_not_be_called():
            nonlocal function_executed
            function_executed = True

        shared_data.base.execute_stage(mock_function_that_should_not_be_called, 'install')
        assert function_executed is False

    def test_get_sso_admin_role_name(self, shared_data):
        """
        Tests that we raise an exception if the sso admin role does not exists and that when it
        does exists, that we return the role name successfully
        :param shared_data: test fixture with SharedData object
        """
        with pytest.raises(Exception) as exception:
            shared_data.base.get_sso_admin_role_name()
        assert str(exception.value) == 'Could not get role name for SSO Consumer Admin'
        self.setup_test_role(SSO_CONSUMER_ADMIN_ROLE_NAME, shared_data.iam_client)
        actual_sso_consumer_admin_role_name = shared_data.base.get_sso_admin_role_name()
        assert actual_sso_consumer_admin_role_name == SSO_CONSUMER_ADMIN_ROLE_NAME

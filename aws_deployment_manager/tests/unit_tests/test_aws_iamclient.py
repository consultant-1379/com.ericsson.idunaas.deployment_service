"""
Unit Tests for AWS IAM Client
"""

import boto3
import pytest

from aws_deployment_manager import utils
from aws_deployment_manager.aws.aws_iamclient import AwsIAMClient


VALID_CONFIG_FILE_PATH = "/workdir/config.yaml"

VALID_OID_URL = "https://server.example.com"

VALID_THUMB_PRINT = "c3768084dfb3d2b68b7897bf5f565da8eEXAMPLE"

EXPECTED_OPEN_ID_PROVIDER = 'arn:aws:iam::000000000000:oidc-provider/server.example.com'

VALID_POLICY = '''
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:Get*",
                "s3:List*"
            ],
            "Resource": [
                "arn:aws:s3:::my-bucket/shared/*"
            ]
        }
    ]
}
'''

EXPECTED_POLICY_ARN = 'arn:aws:iam::000000000000:policy/test_policy'

VALID_ROLE = '{}'

VALID_ROLE_NAME = 'test_role'


# pylint: disable=no-self-use
# pylint: disable=protected-access
@pytest.mark.usefixtures("setup_config_file")
class TestAwsIamClient:
    """
    Class to run tests for AWS IAM Client.
    """

    @staticmethod
    def iam_client_command_fails_mock(**kwargs):
        """
        Mock of any IAM command that responds with a 500 HTTP status code.
        :param kwargs:
        :return: response
        :rtype: dict
        """
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 500,
            },
            'OpenIDConnectProviderArn': 'dummy'
        }

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
                config = utils.load_yaml(VALID_CONFIG_FILE_PATH)
                self.aws_iamclient = AwsIAMClient(config=config)
                self.iam_client = boto3.client('iam')

        return SharedData()

    def test_create_open_id_connect_provider(self, shared_data):
        """
        Tests that we can create an open ID connect provider successfully.
        :param shared_data: test fixture with SharedData object
        """
        actual_open_id_provider = shared_data.aws_iamclient. \
            create_open_id_connect_provider(VALID_OID_URL, VALID_THUMB_PRINT, 'dummyEnv')
        assert actual_open_id_provider == EXPECTED_OPEN_ID_PROVIDER

    def test_create_open_id_connect_provider_already_exists(self, shared_data):
        """
        Tests that we handle the scenario where when we try to create an open ID connect provider,
        it already exists.
        :param shared_data: test fixture with SharedData object
        """
        actual_open_id_provider = shared_data.aws_iamclient. \
            create_open_id_connect_provider(VALID_OID_URL, VALID_THUMB_PRINT, 'dummyEnv')
        assert actual_open_id_provider is None

    def test_create_open_id_connect_provider_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to create an open ID connect provider,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "create_open_id_connect_provider", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.create_open_id_connect_provider(VALID_OID_URL,
                                                                      VALID_THUMB_PRINT, 'dummyEnv')
        assert str(exception.value) == 'Failed to create Open_id_provider for dummyEnv'

    def test_create_policy(self, shared_data):
        """
        Tests that we can create a policy successfully.
        :param shared_data: test fixture with SharedData object
        """
        actual_policy_arn = shared_data.aws_iamclient. \
            create_policy('test_policy', VALID_POLICY, 'dummyEnv')
        assert actual_policy_arn == EXPECTED_POLICY_ARN

    def test_create_policy_already_exists(self, shared_data):
        """
        Tests that we handle the scenario where when we try to create a new policy,
        it already exists.
        :param shared_data: test fixture with SharedData object
        """
        actual_policy_arn = shared_data.aws_iamclient. \
            create_policy('test_policy', VALID_POLICY, 'dummyEnv')
        assert actual_policy_arn is None

    def test_create_policy_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to create a new policy,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "create_policy", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.create_policy('test_policy', VALID_POLICY, 'dummyEnv')
        assert str(exception.value) == 'Failed to create policy test_policy  for dummyEnv'

    def test_create_role(self, shared_data):
        """
        Tests that we can create a role successfully.
        :param shared_data: test fixture with SharedData object
        """
        actual_role_arn = shared_data.aws_iamclient. \
            create_role(VALID_ROLE_NAME, VALID_ROLE, 'dummyEnv')
        expected_role_arn = 'arn:aws:iam::000000000000:role/test_role'
        assert actual_role_arn == expected_role_arn

    def test_create_role_already_exists(self, shared_data):
        """
        Tests that we handle the scenario where when we try to create a new role,
        it already exists.
        :param shared_data: test fixture with SharedData object
        """
        actual_role_arn = shared_data.aws_iamclient. \
            create_role(VALID_ROLE_NAME, VALID_ROLE, 'dummyEnv')
        assert actual_role_arn is None

    def test_create_role_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to create a new role,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "create_role", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.create_role(VALID_ROLE_NAME, VALID_ROLE, 'dummyEnv')
        assert str(exception.value) == 'Failed to create Role test_role for dummyEnv'

    def test_retrieve_list_of_roles(self, shared_data):
        """
        Tests that we can retrieve a list of roles successfully.
        :param shared_data: test fixture with SharedData object
        """
        roles = shared_data.aws_iamclient.list_roles("DummyEnv")
        assert len(roles) == 1
        actual_role_name = roles[0]['RoleName']
        assert actual_role_name == VALID_ROLE_NAME

    def test_retrieve_list_of_roles_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to retrieve a list of roles,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "list_roles", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.list_roles("DummyEnv")
        expected_exception = 'Failed to list Roles for deployment DummyEnv'
        assert str(exception.value) == expected_exception

    def test_retrieve_list_of_policies(self, shared_data):
        """
        Tests that we can retrieve a list of policies successfully.
        :param shared_data: test fixture with SharedData object
        """
        policies = shared_data.aws_iamclient.list_policies("DummyEnv")
        assert len(policies) > 0
        assert 'PolicyName' in policies[0]
        assert 'PolicyId' in policies[0]
        assert 'Arn' in policies[0]

    def test_retrieve_list_of_policies_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to retrieve a list of policies,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "list_policies", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.list_policies("DummyEnv")
        expected_exception = 'Failed to list Policies for deployment DummyEnv'
        assert str(exception.value) == expected_exception

    def test_retrieve_list_of_open_id_connect_providers(self, shared_data):
        """
        Tests that we can retrieve a list of Open ID Connect Providers successfully.
        :param shared_data: test fixture with SharedData object
        """
        open_id_connect_providers = shared_data.aws_iamclient\
            .list_open_id_connect_providers("DummyEnv")
        assert len(open_id_connect_providers) == 1
        assert open_id_connect_providers[0]['Arn'] == EXPECTED_OPEN_ID_PROVIDER

    def test_retrieve_list_of_open_id_connect_providers_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to retrieve a list of Open ID Connect
        Providers, it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "list_open_id_connect_providers", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.list_open_id_connect_providers("DummyEnv")
        expected_exception = 'Failed to list OIDC for deployment DummyEnv'
        assert str(exception.value) == expected_exception

    def test_attach_role_policy(self, shared_data):
        """
        Tests that we can attach a role to a policy successfully.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            attach_role_policy(VALID_ROLE_NAME, EXPECTED_POLICY_ARN)
        assert response is None

    def test_attach_role_policy_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to attach a role to a policy,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "attach_role_policy", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.attach_role_policy(VALID_ROLE_NAME, EXPECTED_POLICY_ARN)
        expected_exception = \
            f'Failed to attach policy {EXPECTED_POLICY_ARN} to Role {VALID_ROLE_NAME} '
        assert str(exception.value) == expected_exception

    def test_detach_role_policy_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to detach a role to a policy,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "detach_role_policy", self.iam_client_command_fails_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient.detach_role_policy(VALID_ROLE_NAME, EXPECTED_POLICY_ARN)
        expected_exception = \
            f'Failed to detach policy {EXPECTED_POLICY_ARN} to Role {VALID_ROLE_NAME} '
        assert str(exception.value) == expected_exception

    def test_detach_role_policy(self, shared_data):
        """
        Tests that we can detach a role to a policy successfully.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            detach_role_policy(VALID_ROLE_NAME, EXPECTED_POLICY_ARN)
        assert response is None

    def test_detach_role_policy_does_not_exist(self, shared_data):
        """
        Tests that we handle the scenario where when we try to detach a role to a policy,
        it does not exist.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            detach_role_policy(VALID_ROLE_NAME, EXPECTED_POLICY_ARN)
        assert response is None

    def test_delete_open_id_connect_provider(self, shared_data):
        """
        Tests that we can delete an Open ID Connect Provider successfully.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            delete_open_id_connect_provider(EXPECTED_OPEN_ID_PROVIDER, 'DummyEnv')
        assert response is None

    def test_delete_open_id_connect_provider_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to delete an Open ID Connect Provider,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "delete_open_id_connect_provider", self.iam_client_command_fails_mock)
        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient. \
                delete_open_id_connect_provider(EXPECTED_OPEN_ID_PROVIDER, 'DummyEnv')
        expected_exception = 'Failed to delete Open_id_provider for DummyEnv deployment'
        assert str(exception.value) == expected_exception

    def test_delete_policy(self, shared_data):
        """
        Tests that we can delete a Policy successfully.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            delete_policy(EXPECTED_POLICY_ARN, 'DummyEnv')
        assert response is None

    def test_delete_policy_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to delete a Policy,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "delete_policy", self.iam_client_command_fails_mock)
        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient. \
                delete_policy(EXPECTED_POLICY_ARN, 'DummyEnv')
        expected_exception = \
            f'Failed to delete policy {EXPECTED_POLICY_ARN}  for deployment DummyEnv'
        assert str(exception.value) == expected_exception

    def test_delete_role(self, shared_data):
        """
        Tests that we can delete a Role successfully.
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            delete_role(VALID_ROLE_NAME, 'DummyEnv')
        assert response is None

    def test_delete_role_does_not_exist(self, shared_data):
        """
        Tests that we handle the scenario where when we try to delete a Role,
        it does not exist
        :param shared_data: test fixture with SharedData object
        """
        response = shared_data.aws_iamclient. \
            delete_role(VALID_ROLE_NAME, 'DummyEnv')
        assert response is None

    def test_delete_role_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario where when we try to delete a Role,
        it fails.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_iamclient._AwsIAMClient__iam_client,
                            "delete_role", self.iam_client_command_fails_mock)
        with pytest.raises(Exception) as exception:
            shared_data.aws_iamclient. \
                delete_role(VALID_ROLE_NAME, 'DummyEnv')
        expected_exception = \
            f'Failed to delete Role {VALID_ROLE_NAME} for DummyEnv'
        assert str(exception.value) == expected_exception

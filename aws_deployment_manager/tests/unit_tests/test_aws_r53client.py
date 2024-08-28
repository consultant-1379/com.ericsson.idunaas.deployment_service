"""
Unit Tests for AWS Route 53 Client
"""
import time

import boto3
import pytest

from aws_deployment_manager import utils
from aws_deployment_manager.aws.aws_r53client import AwsR53Client

VALID_CONFIG_FILE_PATH = "/workdir/config.yaml"

VALID_HOSTED_ZONE_NAME = 'test_hosted_zone_name'

VALID_AWS_REGION = 'eu-west-1'

VALID_RECORD_SETS = [
    {
    "Name": "gas.eo.test.ericsson.se.",
    "Type": "A",
    "AliasTarget": {
        "HostedZoneId": "Z2IFOLAFXgfjh4F",
        "DNSName": "a9d010ec14ecd4a7ead9d5066a3e58.elb.eu-west-1.amazonaws.com.",
        "EvaluateTargetHealth": False
    }
    },
    {
        "Name": "iam.eo.test.ericsson.se.",
        "Type": "A",
        "AliasTarget": {
            "HostedZoneId": "Z2IFOdfgXWLO4F",
            "DNSName": "a9d010ec14ecd4a7ead958.elb.eu-west-1.amazonaws.com.",
            "EvaluateTargetHealth": False
        }
    }
]


# pylint: disable=no-self-use
# pylint: disable=protected-access
@pytest.mark.usefixtures("setup_config_file")
class TestAwsIamClient:
    """
    Class to run tests for AWS IAM Client.
    """

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
                self.aws_r53client = AwsR53Client(config=config)
                self.r53_client = boto3.client('route53')
                ec2_client = boto3.client('ec2')
                vpcs = ec2_client.describe_vpcs()
                self.vpc_id = vpcs['Vpcs'][0]['VpcId']

        return SharedData()

    # pylint: disable=unused-argument
    @staticmethod
    def bad_response_to_command_mock(**kwargs):
        """
        Mocks a bad response from Route53 command
        :param kwargs:
        """
        return {}

    @staticmethod
    def helper_create_hosted_zone(shared_data):
        """
        Helper function that creates a hosted zone and adds the correct output to the response as
        localstack does not provide the expected output
        :param shared_data: test fixture with SharedData object
        :return: create_response, hosted_zone_id
        :rtype: dict, string
        """
        create_response = shared_data.r53_client.create_hosted_zone(
            Name=VALID_HOSTED_ZONE_NAME,
            VPC={
                'VPCRegion': VALID_AWS_REGION,
                'VPCId': shared_data.vpc_id
            },
            CallerReference='randomRef123dsfg',
        )
        hosted_zone_id = create_response['HostedZone']['Id']
        create_response['ChangeInfo'] = {
            'Id': hosted_zone_id,
            'Status': 'INSYNC'
        }
        return create_response, hosted_zone_id

    def test_hosted_zone_exists(self, shared_data):
        """
        Tests that if a zone exists we can see it and if there are none, we also catch that.
        :param shared_data: test fixture with SharedData object
        """
        _, hosted_zone_id = self.helper_create_hosted_zone(shared_data)

        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is True

        shared_data.r53_client.delete_hosted_zone(Id=hosted_zone_id)
        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is False

    def test_create_hosted_zone(self, shared_data, monkeypatch):
        """
        Tests that we can create a hosted zone successfully.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        hosted_zone_id = None

        # pylint: disable=unused-argument
        def create_hosted_zone_mock(**kwargs):
            """
            Mock that creates a hosted zone as we cannot create one with PrivateZone set to True
            :param kwargs:
            """
            nonlocal hosted_zone_id
            create_response, hosted_zone_id = self.helper_create_hosted_zone(shared_data)
            return create_response

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "create_hosted_zone", create_hosted_zone_mock)

        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is False

        shared_data.aws_r53client.create_hosted_zone(VALID_HOSTED_ZONE_NAME, shared_data.vpc_id)

        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is True

        shared_data.r53_client.delete_hosted_zone(Id=hosted_zone_id)

    def test_create_hosted_zone_fails(self, shared_data, monkeypatch):
        """
        Tests that we can handle an error when creating a hosted zone.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        # pylint: disable=unused-argument
        def create_hosted_zone_mock(**kwargs):
            """
            Mocks a bad response from create hosted zone command
            :param kwargs:
            """
            return {}

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "create_hosted_zone", create_hosted_zone_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client.create_hosted_zone(VALID_HOSTED_ZONE_NAME, shared_data.vpc_id)
        expected_exception_value = f'Error in creating hosted zone {VALID_HOSTED_ZONE_NAME}. ' \
                                   f'No ChangeInfo object in response'
        assert str(exception.value) == expected_exception_value

    def test_get_hosted_zone_id(self, shared_data, monkeypatch):
        """
        Tests that we can get a hosted zone id successfully.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        _, expected_hosted_zone_id = self.helper_create_hosted_zone(shared_data)

        actual_hosted_zone_id = shared_data.aws_r53client.get_hosted_zone_id(VALID_HOSTED_ZONE_NAME)

        assert actual_hosted_zone_id == expected_hosted_zone_id

        shared_data.r53_client.delete_hosted_zone(Id=expected_hosted_zone_id)

    def test_get_hosted_zone_id_does_not_exists(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario when getting a hosted zone id, there are no hosted zones
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client.get_hosted_zone_id('doesNotExist')
        expected_exception_value = 'Hosted Zone doesNotExist does not exist'
        assert str(exception.value) == expected_exception_value

    def test_delete_hosted_zone(self, shared_data, monkeypatch):
        """
        Tests that we can delete a hosted zone id successfully.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        _, hosted_zone_id = self.helper_create_hosted_zone(shared_data)

        # pylint: disable=unused-argument
        def delete_hosted_zone_mock(**kwargs):
            """
            Mock for delete hosted zone as localstack does not provide the correct output for the
            delete command
            :param kwargs:
            :return: delete response
            :rtype: dict
            """
            nonlocal hosted_zone_id
            delete_response = shared_data.r53_client.delete_hosted_zone(
                Id=hosted_zone_id
            )
            delete_response['ChangeInfo'] = {
                'Id': hosted_zone_id,
                'Status': 'INSYNC'
            }
            return delete_response

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "delete_hosted_zone", delete_hosted_zone_mock)
        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is True
        response = shared_data.aws_r53client.delete_hosted_zone(VALID_HOSTED_ZONE_NAME)
        hosted_zone_exists = shared_data.aws_r53client.hosted_zone_exists(VALID_HOSTED_ZONE_NAME)
        assert hosted_zone_exists is False
        assert response['ChangeInfo']['Id'] == hosted_zone_id
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def test_delete_hosted_zone_does_not_exist(self, shared_data):
        """
        Tests that we handle the scenario when we try to delete a hosted zone and it does not exist
        :param shared_data: test fixture with SharedData object
        """

        response = shared_data.aws_r53client.delete_hosted_zone(VALID_HOSTED_ZONE_NAME)
        assert response is None

    def test_delete_hosted_zone_fails(self, shared_data, monkeypatch):
        """
        Tests that we can handle an error when deleting a hosted zone.
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        _, hosted_zone_id = self.helper_create_hosted_zone(shared_data)

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "delete_hosted_zone", self.bad_response_to_command_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client.delete_hosted_zone(VALID_HOSTED_ZONE_NAME)

        shared_data.r53_client.delete_hosted_zone(Id=hosted_zone_id)
        expected_exception_value = f'Error in deleting hosted zone {VALID_HOSTED_ZONE_NAME}. ' \
                                   f'No ChangeInfo object in response'
        assert str(exception.value) == expected_exception_value

    def test_get_resource_record_sets(self, shared_data):
        """
        Tests that we can get the resource record sets for a hosted zone
        :param shared_data: test fixture with SharedData object
        """
        _, hosted_zone_id = self.helper_create_hosted_zone(shared_data)
        record_sets = shared_data.aws_r53client._get_resource_record_sets(hosted_zone_id,
                                                                             VALID_HOSTED_ZONE_NAME)
        shared_data.r53_client.delete_hosted_zone(Id=hosted_zone_id)
        assert len(record_sets) == 0

    def test_get_resource_record_sets_fails(self, shared_data, monkeypatch):
        """
        Tests that we can handle an error when getting the resource record sets for a hosted zone
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """
        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "list_resource_record_sets", self.bad_response_to_command_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client._get_resource_record_sets('1234', VALID_HOSTED_ZONE_NAME)

        expected_exception_value = f'Could not delete hosted zone. Failed to get records ' \
                                   f'from hosted zone {VALID_HOSTED_ZONE_NAME}'
        assert str(exception.value) == expected_exception_value

    def test_delete_records_of_hosted_zone(self, shared_data, monkeypatch):
        """
        Tests that we can delete records of a hosted zone successfully
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        # pylint: disable=unused-argument
        def change_resource_record_sets_mock(**kwargs):
            """
            Mocks change_resource_record_sets as Localstack does not have this method implemented
            :param kwargs:
            :return: response
            :rtype: dict
            """
            return {
                'ChangeInfo': {
                    'Id': 'test_id',
                    'Status': 'INSYNC'
                }
            }

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "change_resource_record_sets", change_resource_record_sets_mock)
        response = shared_data.aws_r53client.\
            _delete_records_of_hosted_zone(VALID_RECORD_SETS, VALID_HOSTED_ZONE_NAME, 'test_id')
        assert response is not None
        assert 'Id' in response['ChangeInfo']
        assert 'Status' in response['ChangeInfo']

    def test_delete_records_of_hosted_zone_fails(self, shared_data, monkeypatch):
        """
        Tests that we handle the scenario when we try to delete records of a hosted zone, it fails
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "change_resource_record_sets", self.bad_response_to_command_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client._delete_records_of_hosted_zone(
                VALID_RECORD_SETS, VALID_HOSTED_ZONE_NAME, 'test_id')

        expected_exception_value = f'Error in deleting records in hosted zone ' \
                                   f'{VALID_HOSTED_ZONE_NAME}. No ChangeInfo object in response'
        assert str(exception.value) == expected_exception_value

    def test_delete_records_of_hosted_zone_none_exist(self, shared_data):
        """
        Tests that we can handle where there are no records to delete
        :param shared_data: test fixture with SharedData object
        """
        _, hosted_zone_id = self.helper_create_hosted_zone(shared_data)
        response = shared_data.aws_r53client.\
            _delete_records_of_hosted_zone([], hosted_zone_id, VALID_HOSTED_ZONE_NAME)
        shared_data.r53_client.delete_hosted_zone(Id=hosted_zone_id)
        assert response is None

    def test_wait_for_change_id_sync(self, shared_data, monkeypatch):
        """
        Tests that wait for change id sync works as expected
        :param shared_data: test fixture with SharedData object
        :param monkeypatch:
        """

        # pylint: disable=unused-argument
        def get_change_completed_mock(**kwargs):
            """
            Mocks get_change and returns a completed change
            :param kwargs:
            :return: response
            :rtype: dict
            """
            return {
                'ChangeInfo': {
                    'Id': 'test_id',
                    'Status': 'INSYNC'
                }
            }

        # pylint: disable=unused-argument
        def get_change_hanging_mock(**kwargs):
            """
            Mocks get_change and returns a change that is hanging
            :param kwargs:
            :return: response
            :rtype: dict
            """
            return {
                'ChangeInfo': {
                    'Id': 'test_id',
                    'Status': 'PENDING'
                }
            }

        # pylint: disable=unused-argument
        def time_sleep_mock(timeout):
            """
            Mocks sleep command of time module so we don't have to wait around
            :param timeout: how long to wait
            """
            timeout = None
            return timeout

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "get_change", get_change_completed_mock)

        monkeypatch.setattr(time, "sleep", time_sleep_mock)

        response = shared_data.aws_r53client._wait_for_change_id_sync('change_id')
        assert response is None

        monkeypatch.setattr(shared_data.aws_r53client._AwsR53Client__r53_client,
                            "get_change", get_change_hanging_mock)

        with pytest.raises(Exception) as exception:
            shared_data.aws_r53client._wait_for_change_id_sync('change_id')

        expected_exception_value = 'Change ID change_id still in PENDING state'
        assert str(exception.value) == expected_exception_value

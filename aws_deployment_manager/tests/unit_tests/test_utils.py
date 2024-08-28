"""
Unit Tests for the utils module.
"""
import filecmp
import shutil
import tempfile

import docker
import pytest

from aws_deployment_manager import utils


VALID_CONFIG_CONTENT = '''EnvironmentName: idun-2
AWSRegion: eu-west-1
VPCID: vpc-00807c28bc36b5100
ControlPlaneSubnetIds: subnet-0d599a3c13b85647c,subnet-080c49a72f13e432d
WorkerNodeSubnetIds: subnet-0d599a3c13b85647c
SecondaryVpcCIDR: 172.32.4.0/22
DisablePublicAccess: true
NodeInstanceType: m5.2xlarge
DiskSize: 20
MinNodes: 8
MaxNodes: 10
SshKeyPairName: test-idun-keypair
PrivateDomainName: idunaas.ericsson.se
K8SVersion: '1.24'
KubeDownscaler: true
BackupInstanceType: t3.medium
BackupAmiId: ami00a40405a13c972f4
BackupDisk: 50
BackupPass: pass
Hostnames:
  so: so.eo.idunaas.ericsson.se
  pf: pf.eo.idunaas.ericsson.se
  iam: iam.eo.idunaas.ericsson.se
  uds: uds.eo.idunaas.ericsson.se
'''


INVALID_CONFIG_YAML_CONTENTS_MISSING_REQUIRED_FIELD = '''
AWSRegion: eu-west-1
VPCID: vpc-00807c28bc36b5100
ControlPlaneSubnetIds: subnet-0d599a3c13b85647c,subnet-080c49a72f13e432d
WorkerNodeSubnetIds: subnet-0d599a3c13b85647c
SecondaryVpcCIDR: 172.32.4.0/22
DisablePublicAccess: True
NodeInstanceType: m5.2xlarge
DiskSize: 20
MinNodes: 8
MaxNodes: 10
SshKeyPairName: test-idun-keypair
PrivateDomainName: idunaas.ericsson.se
K8SVersion: '1.24'
KubeDownscaler: true
BackupInstanceType: t3.medium
BackupAmiId: ami00a40405a13c972f4
BackupDisk: 50
BackupPass: pass
Hostnames:
  so: so.eo.idunaas.ericsson.se
  pf: pf.eo.idunaas.ericsson.se
  iam: iam.eo.idunaas.ericsson.se
  uds: uds.eo.idunaas.ericsson.se
'''

INVALID_CONFIG_YAML_CONTENTS_WITH_INVALID_VALUES = '''
EnvironmentName: idun-2
AWSRegion: eu-west-1
VPCID: vpc-00807c28bc36b5100
ControlPlaneSubnetIds: subnet-0d599a3c13b85647c
WorkerNodeSubnetIds: "subnet-0d599a3c13b85647c,subnet-0d599a3c13b85647c,subnet-0d599a3c13b85647c"
SecondaryVpcCIDR: 172.32.4.0/22
DisablePublicAccess: True
NodeInstanceType: m5.2xlarge
DiskSize: 20
MinNodes: 8
MaxNodes: 10
SshKeyPairName: test-idun-keypair
PrivateDomainName: idunaas.ericsson.se
K8SVersion: '1.24'
KubeDownscaler: true
BackupInstanceType: t3.medium
BackupAmiId: ami00a40405a13c972f41
BackupDisk: 50
BackupPass: pass
Hostnames:
  so: so.eo.idunaas.ericsson.se
  pf: pf.eo.idunaas.ericsson.se
  iam: iam.eo.idunaas.ericsson.se
  uds: uds.eo.idunaas.ericsson.se
'''

VALID_STACK_DETAILS = {
    'Stacks': [{
        'Outputs': [{
            'OutputKey': 'sampleOutputKey',
            'OutputValue': 'sampleOutputValue'
        }],
        'Parameters': [{
            'ParameterKey': 'sampleParameterKey',
            'ParameterValue': 'sampleParameterValue'
        }]
    }]
}

EXPECTED_STACK_OUTPUTS = {
    'sampleOutputKey': 'sampleOutputValue'
}

EXPECTED_STACK_PARAMETERS = {
    'sampleParameterKey': 'sampleParameterValue'
}

VALID_CLUSTER_NAME = "idun2-EKS-Cluster"

VALID_STACK_NAME = "idun2"

VALID_DOCKER_CONFIG = '''{
  "https://armdockerhub.rnd.ericsson.se": {
    "auth": "jhsdgfgjhfgkjsdakfjasjklhf",
    "email": "someemail@some.com"
  }
}'''

VALID_JSON_FILE_CONTENTS = '{"test": "it works!"}'


# pylint: disable=too-few-public-methods
class ImagesMock:
    """
    Class to mock the docker images module.
    """
    @staticmethod
    def pull(url):
        """
        Mocks the pull method for the docker images module.
        If the URL matches the expected URL, it raises an exception to show we got to the URl.
        """
        if url == 'successfulUrl/proj-idun-aas/image_should_not_exist':
            raise docker.errors.NotFound('Fail')


# pylint: disable=too-few-public-methods
class DockerClientMock:
    """
    Class to mock the docker client module
    """
    @property
    def images(self):
        """
        Mocks the image pull method.
        :return images_mock: a mock object with a pull method.
        :rtype: ImagesMock
        """
        return ImagesMock()


# pylint: disable=no-self-use
class TestUtils:
    """
    Class to run tests for the utils module.
    """
    test_dir = tempfile.mkdtemp()
    test_file_path = test_dir + '/test.txt'
    valid_config_file_path = test_dir + "/config.yaml"
    valid_path_for_config_file_to_be_written = test_dir + "/configWritten.yaml"
    invalid_config_file_path = test_dir + "/invalid_config.yaml"
    valid_json_file_path = test_dir + "/valid_json_file.json"
    mock_user_home = None

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """
        Sets up config for running tests and cleans up after the tests are done.
        """
        utils.USER_HOME = self.test_dir
        self.setup_valid_json_file()
        self.setup_valid_config_file()
        yield
        shutil.rmtree(self.test_dir)

    def setup_invalid_config_file(self, content):
        """
        Creates an invalid config file for running tests.
        :param content: The content to write to the config file.
        """
        with open(self.invalid_config_file_path, 'w') as file:
            file.writelines(content)

    def setup_valid_config_file(self):
        """
        Creates an valid config file for running tests.
        """
        with open(self.valid_config_file_path, 'w') as file:
            file.writelines(VALID_CONFIG_CONTENT)

    def setup_valid_json_file(self):
        """
        Creates an valid generic JSON file for running tests.
        """
        with open(self.valid_json_file_path, 'w') as file:
            file.writelines(VALID_JSON_FILE_CONTENTS)

    def test_read_file(self):
        """
        Tests that we can read a file correctly.
        """
        expected_file_contents = "This is a test"
        with open(self.test_file_path, "a") as file:
            file.write(expected_file_contents)
        actual_file_contents = utils.read_file(self.test_file_path)
        assert actual_file_contents == expected_file_contents

    def test_load_config(self):
        """
        Tests that we can load the config from a config file correctly.
        """
        config = utils.load_yaml(self.valid_config_file_path)
        expected_parameters = ["EnvironmentName", "AWSRegion", "ControlPlaneSubnetIds",
                               "WorkerNodeSubnetIds", "SecondaryVpcCIDR", "NodeInstanceType",
                               "DiskSize", "MinNodes", "SshKeyPairName", "PrivateDomainName",
                               "Hostnames", "K8SVersion", "KubeDownscaler"]
        assert [parameter in config for parameter in expected_parameters]

    def test_validate_idun_config(self):
        """
        Tests that the validation of the idun config file is working as expected.
        """
        valid_config = utils.load_yaml(self.valid_config_file_path)
        is_valid, validation_errors = utils.validate_idun_config(valid_config)
        assert is_valid is True
        assert len(validation_errors) == 0

    def test_validate_idun_invalid_config_required_field(self):
        """
        Tests that we catch that we are missing required fields during the validation of the idun
        config file.
        """
        self.setup_invalid_config_file(INVALID_CONFIG_YAML_CONTENTS_MISSING_REQUIRED_FIELD)
        invalid_config = utils.load_yaml(self.invalid_config_file_path)
        is_valid, validation_errors = utils.validate_idun_config(invalid_config)
        expected_error = "Schema Error for Parameter EnvironmentName. Error - ['required field']"
        assert is_valid is False
        assert len(validation_errors) == 1
        assert expected_error in validation_errors

    def test_validate_idun_invalid_config_invalid_fields(self):
        """
        Tests that we catch that we have invalid fields during the validation of the idun
        config file.
        """
        self.setup_invalid_config_file(INVALID_CONFIG_YAML_CONTENTS_WITH_INVALID_VALUES)
        invalid_config = utils.load_yaml(self.invalid_config_file_path)
        is_valid, validation_errors = utils.validate_idun_config(invalid_config)
        expected_errors = [
            'Minimum 1 and Maximum 2 Worker Node Subnet IDs to be provided. 3 provided',
            '2 Control Plane Subnet IDs to be provided. 3 provided'
        ]
        assert is_valid is False
        assert len(validation_errors) == 2
        assert [expected_error in validation_errors for expected_error in expected_errors]

    def test_get_stack_outputs(self):
        """
        Tests that we can get the stack outputs from stack details correctly.
        """
        actual_stack_outputs = utils.get_stack_outputs(VALID_STACK_DETAILS)
        assert actual_stack_outputs == EXPECTED_STACK_OUTPUTS
        actual_stack_outputs = utils.get_stack_outputs(None)
        assert actual_stack_outputs == {}

    def test_get_stack_parameters(self):
        """
        Tests that we can get the stack parameters from stack details correctly.
        """
        actual_stack_parameters = utils.get_stack_parameters(VALID_STACK_DETAILS)
        assert actual_stack_parameters == EXPECTED_STACK_PARAMETERS
        actual_stack_parameters = utils.get_stack_parameters(None)
        assert actual_stack_parameters == {}

    def test_execute_command(self):
        """
        Tests that we can execute a shell command correctly.
        """
        output = utils.execute_command("echo 'Hello World'")
        assert output == "Hello World\n"
        with pytest.raises(Exception) as exception:
            utils.execute_command("exit 1")
        assert str(exception.value) == 'Failed to execute command - exit 1. Error is - '

    def test_get_stack_name_from_cluster(self):
        """
        Tests that we can get the stack name from a cluster name correctly.
        """
        actual_stack_name = utils.get_stack_name_from_cluster(VALID_CLUSTER_NAME)
        assert actual_stack_name == VALID_STACK_NAME

    def test_get_cluster_name_from_stack(self):
        """
        Tests that we can get the cluster name from a stack name correctly.
        """
        actual_stack_cluster_name = utils.get_cluster_name_from_stack(VALID_STACK_NAME)
        assert actual_stack_cluster_name == VALID_CLUSTER_NAME

    def test_write_config_file(self):
        """
        Tests that given a config, we can write that config to a file correctly.
        """
        valid_config = utils.load_yaml(self.valid_config_file_path)
        utils.write_yaml(self.valid_path_for_config_file_to_be_written, valid_config)

        assert filecmp.cmp(self.valid_path_for_config_file_to_be_written,
                           self.valid_config_file_path)

    def test_test_docker_registry_login(self, monkeypatch):
        """
        Tests that we can get the cluster name from a stack name correctly.
        :param monkeypatch: test fixture that allows mocking
        """
        def helper_get_docker_mock():
            """
            Mocks the get docker client method.
            :return docker_mock:
            :rtype: DockerClientMock
            """
            docker_mock = DockerClientMock()
            return docker_mock
        monkeypatch.setattr(docker, "from_env", helper_get_docker_mock)
        utils.test_docker_registry_login('successfulUrl', 'someUser', 'somePassword')
        with pytest.raises(Exception) as exception:
            utils.test_docker_registry_login('unsuccessfulUrl', 'someUser', 'somePassword')
        assert str(exception.value) == "Failed verifying connection to the docker registry " \
                                       "'unsuccessfulUrl' with the following error: There was " \
                                       "an unexpected response from the docker registry"

    def test_base64_encoder(self):
        """
        Tests that we can base64 encode a string correctly.
        """
        actual_encoded_secret = utils.base64_encoder('a_great_secret')
        expected_encoded_secret = 'YV9ncmVhdF9zZWNyZXQ='
        assert actual_encoded_secret == expected_encoded_secret

    def test_create_docker_config_json_file(self):
        """
        Tests that given a docker config, we can create a docker config json file with that config.
        """
        utils.create_docker_config_json_file(VALID_DOCKER_CONFIG)
        actual_docker_config_file_contents = open(self.test_dir + '/.docker/config.json').read()
        assert actual_docker_config_file_contents == VALID_DOCKER_CONFIG

    def test_load_json_string(self):
        """
        Tests that given a string that contains JSON content, we can convert it to a dictionary.
        """
        actual_json_file_content = utils.load_json_string(self.valid_json_file_path)
        assert actual_json_file_content == VALID_JSON_FILE_CONTENTS

    def test_write_file(self):
        """
        Tests that we can write content to a file correctly.
        """
        file_path = self.test_dir + "/itsAFile.json"
        utils.write_file(file_path, VALID_JSON_FILE_CONTENTS)
        actual_file_contents = open(file_path).read()
        assert actual_file_contents == VALID_JSON_FILE_CONTENTS

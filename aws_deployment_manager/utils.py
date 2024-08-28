"""This module contains a list of utility functions."""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
import subprocess
import os
import base64
import yaml
import docker
import boto3
from cerberus import Validator
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)
USER_HOME = str(Path.home())


def get_log_level_from_verbosity(verbosity):
    """Return a log level based on a given verbosity number."""
    log_levels = {
        0: logging.CRITICAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }
    return log_levels.get(verbosity, "Invalid verbosity level")


def initialize_logging(verbosity, working_directory, logs_sub_directory, filename_postfix):
    """
    Initialize the logging to standard output and standard out at different verbosities.

    Returns the log file path relative to the working directory.
    """
    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s"
    absolute_log_directory = Path(working_directory) / Path(logs_sub_directory)
    absolute_log_directory.mkdir(parents=True, exist_ok=True)
    relative_log_file_path = str(Path(logs_sub_directory) / datetime.now().strftime(
        '%Y-%m-%dT%H_%M_%S%z_{0}.log'.format(filename_postfix))
                                )
    absolute_log_file_path = str(Path(working_directory) / Path(relative_log_file_path))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(log_format))
    stream_handler.setLevel(get_log_level_from_verbosity(verbosity))
    logging.basicConfig(filename=absolute_log_file_path, format=log_format, level=logging.DEBUG)
    logging.getLogger('').addHandler(stream_handler)
    logging.getLogger("botocore").setLevel(logging.INFO)
    return relative_log_file_path


def read_file(file_path):
    """
    Reads a file
    :param file_path: Path to file
    :return: Contents of file
    """
    with open(file_path, "r") as file:
        return file.read()


def load_yaml(file_path):
    """
    Loads data from YAML file
    :param: Path of YAML file
    :return: Dictionary Object with data read from file
    """
    with open(file_path, "rb") as file:
        config = yaml.safe_load(file)
    return config

def write_yaml(file_path, data):
    """
    Write data into yaml file as output
    :param file_path:    Path to YAML file to be created
    :param data:         Dictionary representation of the data
    """
    with open(file_path, 'w') as outfile:
        yaml.dump(data, outfile,
                  default_flow_style=False,
                  sort_keys=False)


def validate_idun_config(config):
    """
    Validate IDUN Configuration Parameters
    :param config: Configuration object
    :return: True if configuration is valid, else returns array of validation errors
    """
    validation_errors = []
    if os.path.exists('./aws_deployment_manager/schema.py'):
        schema = eval(open('./aws_deployment_manager/schema.py', 'r').read())
    else:
        schema = eval(open('/venv/aws_deployment_manager/schema.py', 'r').read())

    validator = Validator(schema)
    configuration_valid = validator.validate(config, schema)

    if not configuration_valid:
        schema_errors = validator.errors
        for param in schema_errors:
            if 'regex' in str(schema_errors[param]):
                validation_errors.append(
                    "Schema Error for Parameter {0}. Error - {1}".format(param, 'Empty String in parameter value'))
            else:
                validation_errors.append(
                    "Schema Error for Parameter {0}. Error - {1}".format(param, schema_errors[param]))

    if len(validation_errors) > 0:
        configuration_valid = False
        return configuration_valid, validation_errors

    # Check that AWS Region is supported
    region = config[constants.AWS_REGION]
    if region not in constants.SUPPORTED_REGIONS:
        validation_errors.append("Region {0} is not supported. Please select region from {1}".
                                 format(region, constants.SUPPORTED_REGIONS))

    # Check that all mandatory parameters are provided
    mandatory_parameters = [constants.ENVIRONMENT_NAME, constants.SECONDARY_VPC_CIDR,
                            constants.NODE_INSTANCE_TYPE, constants.PRIVATE_DOMAIN_NAME]

    for param in mandatory_parameters:
        if not str(config[param]).strip():
            validation_errors.append("Missing Mandatory Parameter - {0}".format(param))

    private_subnet_ids = config[constants.WORKER_NODE_SUBNET_IDS].split(",")
    if len(private_subnet_ids) > 2 or len(private_subnet_ids) < 1:
        validation_errors.append("Minimum 1 and Maximum 2 Worker Node Subnet IDs to be provided. {0} provided".
                                 format(len(private_subnet_ids)))

    control_plane_subnet_ids = config[constants.CONTROL_PLANE_SUBNET_IDS].split(",")
    if len(control_plane_subnet_ids) != 2:
        validation_errors.append("2 Control Plane Subnet IDs to be provided. {0} provided".
                                 format(len(private_subnet_ids)))

    # secondary_cidr = str(config[constants.SECONDARY_VPC_CIDR])
    # if not secondary_cidr.endswith("/22"):
    #     validation_errors.append("Parameter {0} must have subnet of /22".format(constants.SECONDARY_VPC_CIDR))

    if len(validation_errors) > 0:
        configuration_valid = False
    return configuration_valid, validation_errors


def log_stack_details(response):
    """
    Log Stack Outputs
    :param response: Stack Details
    """
    if response is not None:
        stack = response['Stacks'][0]
        outputs = stack['Outputs']

        details = "\n"
        details += "Stack Name = {0}".format(stack['StackName'])
        details += "\n"
        details += "Outputs"
        details += "\n"
        details += "====================="
        details += "\n"

        if outputs:
            for out in outputs:
                details += ("\t{0} ({1}) - {2}".format(out['OutputKey'], out['Description'], out['OutputValue']))
                details += "\n"

        LOG.info("{0}".format(details))


def get_stack_outputs(stack_details):
    """
    Get Stack Output Dictionary Object from Stack Details received from Cloudformation
    :param stack_details: Stack Details
    :return: Stack Outputs
    """
    stack_outputs = {}
    if stack_details is not None:
        stack = stack_details['Stacks'][0]
        if 'Outputs' in stack:
            for out in stack['Outputs']:
                key = out['OutputKey']
                value = out['OutputValue']
                stack_outputs[key] = value

    return stack_outputs


def get_stack_parameters(stack_details):
    """
    Get Stack Parameters Dictionary Object from Stack Details received from Cloudformation
    :param stack_details: Stack Details
    :return: Stack Parameters
    """
    stack_parameters = {}
    if stack_details is not None:
        stack = stack_details['Stacks'][0]
        parameters = stack['Parameters']

        if parameters:
            for param in parameters:
                key = param['ParameterKey']
                value = param['ParameterValue']
                stack_parameters[key] = value

    return stack_parameters


def execute_command(command):
    """
    Execute a command on shell
    :param command: Command to be executed
    :return: Command Response
    """
    LOG.info("Executing command - {0}".format(command))

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout_value = proc.communicate()[0].decode("utf-8")

    LOG.info("Command Output - ")
    LOG.info("{0}".format(stdout_value))
    return_value = proc.returncode
    LOG.info("Return Code = {0}".format(return_value))

    if return_value != 0:
        raise Exception("Failed to execute command - {0}. Error is - {1}".format(command, stdout_value))

    return stdout_value


def get_stack_name_from_cluster(cluster_name):
    """
    Get IDUN Stack name from EKS Cluster Name
    :param cluster_name: Name of EKS Cluster
    :return: Name of IDUN Stack
    """
    return cluster_name.replace(constants.CLUSTER_NAME_POSTFIX,'')


def get_cluster_name_from_stack(stack_name):
    """
    Get IDUN EKS Cluster Name from IDUN Stack Name
    :param stack_name: Name of IDUN Environment or STack
    :return: Name of EKS Cluster
    """
    return stack_name + constants.CLUSTER_NAME_POSTFIX


def test_docker_registry_login(registry_url, registry_user, registry_password):
    """
    Tests connection to Docker Registry with username and password
    :param registry_url: URL of Docker Registry
    :param registry_user: Username
    :param registry_password: Password
    :return: True if connection is successful, else raise Exception
    """
    docker_config_json = create_docker_config_json(registry_url, registry_user, registry_password)
    create_docker_config_json_file(docker_config_json=docker_config_json)
    client = docker.from_env()
    try:
        LOG.info("Started verifying connection to the docker registry {0}".format(registry_url))
        client.images.pull(registry_url + '/proj-idun-aas/image_should_not_exist')
        raise Exception("There was an unexpected response from the docker registry")
    except docker.errors.NotFound:
        LOG.info("Completed verifying connection to the docker registry {0}".format(registry_url))
    except Exception as exception:
        raise Exception(
            ("Failed verifying connection to the docker registry '{0}' " +
             "with the following error: {1}").format(registry_url, str(exception))) \
            from exception


def create_docker_config_json(registry_url, registry_user, registry_password):
    """Create a docker config json."""
    docker_config_json = '{"auths":{"%s":{"username":"%s","password":"%s","auth":"%s"}}}' % \
                         (registry_url, registry_user, registry_password,
                          base64_encoder("%s:%s" % (registry_user, registry_password)))
    return docker_config_json


def base64_encoder(unencoded_value):
    """Encode a string to base64 string."""
    return base64.b64encode(unencoded_value.encode()).decode('utf-8')


def create_docker_config_json_file(docker_config_json):
    """Write the docker config."""
    docker_config_json_file_path = '{0}/.docker/config.json'.format(USER_HOME)
    LOG.info("Creating docker config file at {0}".format(docker_config_json_file_path))
    Path(docker_config_json_file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(docker_config_json_file_path, "w") as docker_config_json_file:
        docker_config_json_file.write(docker_config_json)


def create_namespace(namespace):
    """
    Creates a namespace in K8S Cluster
    :param namespace: Name of namespace
    """
    LOG.info("Creating namespace {0}...".format(namespace))

    # Check if namespace already exists
    if not namespace_exists(namespace=namespace):
        command = constants.COMMAND_CREATE_NAMESPACE.format(namespace, constants.KUBECONFIG_PATH)
        execute_command(command=command)
        LOG.info("Created namespace {0}".format(namespace))
        return

    LOG.info("Namespace {0} already exists".format(namespace))


def namespace_exists(namespace):
    """
    Checks if a namespace already exists in K8S cluster
    :param namespace: Name of namespace
    :return: True if present else False
    """
    command = constants.COMMAND_GET_ALL_NAMESPACES.format(constants.KUBECONFIG_PATH)
    command_output = execute_command(command=command)

    if namespace in command_output:
        return True
    return False


def load_json_string(json_file_path):
    """
    Load json File and output as String
    :return: Json File as String
    """
    with open(json_file_path) as file:
        policy_json = json.load(file)

    policy_string = json.dumps(policy_json)
    return policy_string


def write_file(file_path, content):
    """
    Write content to a File
    :return:
    """
    with open(file_path, 'w') as file:
        file.write(content)


def generate_kube_config_file(cluster_name, region, config_file_path):
    """
    Generate Kubeconfig file for EKS Cluster
    :param cluster_name: Name of EKS Cluster
    :param region: AWS Region of EKS Cluster
    :param config_file_path: Path of Kubeconfig file
    :return: None
    """
    # First delete any old config file
    if os.path.exists(config_file_path):
        os.remove(config_file_path)

    command = constants.COMMAND_KUBECTL_UPDATE_CONFIG.format(
        cluster_name,
        region,
        config_file_path)

    execute_command(command=command)

    if not os.path.exists(config_file_path):
        raise Exception("Failed to generate Kube Config for Admin User")

    LOG.info("K8S Config File generated at {0}".format(config_file_path))
    execute_command(command='chmod 0600 ' + config_file_path)


def get_nodes_in_cluster():
    """
    Get List of nodes in K8S Cluster
    :return: Name of nodes
    """
    node_list = []
    command = constants.COMMAND_GET_NODES.format(constants.KUBECONFIG_PATH)
    response = execute_command(command=command)
    nodes = response.split("\n")
    for node in nodes[1:]:
        temp = node.split(" ")
        if temp[0]:
            node_list.append(temp[0])

    return node_list


def cordon_node(node_name, kubeconfig_path):
    """
    Cordon a node in K8S Cluster
    :param node_name: Name of node
    :param kubeconfig_path: Path of kubeconfig
    """
    command = constants.COMMAND_CORDON_NODE.format(node_name, kubeconfig_path)
    execute_command(command=command)


def uncordon_node(node_name, kubeconfig_path):
    """
    Un-Cordon a node in K8S Cluster
    :param node_name: Name of node
    :param kubeconfig_path: Path of kubeconfig
    """
    command = constants.COMMAND_UNCORDON_NODE.format(node_name, kubeconfig_path)
    execute_command(command=command)


def drain_node(node_name, kubeconfig_path):
    """
    Drain a node in K8S Cluster
    :param node_name: Name of node
    :param kubeconfig_path: Path of kubeconfig
    """
    command = constants.COMMAND_DRAIN_NODE.format(node_name, kubeconfig_path)
    try:
        execute_command(command=command)
    except Exception as error:
        LOG.error("Drain failed for node {0}. Error = {1}".format(node_name, error))
        LOG.info("Retrying drain of node {0}".format(node_name))
        command = command + " --disable-eviction=true"
        execute_command(command=command)


def get_unhealthy_pods(kubeconfig_path):
    """
    Check if all PODs in K8S are healthy or not
    :param kubeconfig_path: Path to kubeconfig file
    :return: True if all PODs are healthy, or False along with zip of namespace and name of unhealthy PODs
    """
    command = constants.COMMAND_GET_UNHEALTHY_PODS.format(kubeconfig_path)
    command_output = execute_command(command=command)

    all_pods_healthy = True
    namespace = []
    name = []

    lines = str(command_output).strip().split("\n")
    if len(lines) == 1:
        LOG.info("All PODs healthy")
    else:
        LOG.info("There are unhealthy PODs")
        all_pods_healthy = False
        for line in lines[1:]:
            temp = line.split()
            namespace.append(temp[0])
            name.append(temp[1])

    unhealthy_pods = zip(namespace, name)
    return all_pods_healthy, unhealthy_pods


def wait_for_all_pods_to_healthy(kubeconfig_path, max_retry=60, seconds_to_sleep=60):
    """
    Wait for all PODs in K8S to be healthy
    :param kubeconfig_path: Path to kubeconfig file
    :return: True if all PODs are healthy, or False if there are unhealthy PODs
    """
    retry_count = 0
    all_pods_healthy = False

    while not all_pods_healthy:
        LOG.info("Waiting for 1 min...")
        time.sleep(seconds_to_sleep)

        LOG.info("Checking PODs health status...")
        all_pods_healthy, _ = get_unhealthy_pods(kubeconfig_path=kubeconfig_path)

        if not all_pods_healthy:
            retry_count += 1

        if retry_count > max_retry:
            break

        LOG.info("Test {0} (max {1} retries)".format(retry_count, max_retry))

    LOG.info("All PODs healthy = {0}".format(all_pods_healthy))
    return all_pods_healthy

def create_file_from_template(file__in, file_out, replacements):
    """
    Create file_out from the content of file__in replacing the key-value pairs
    in replacements
    :param file__in:         Path to the template
    :param file_out:         Path to the file that will be created
    :param replacements:     Dictionary of the replacements (each key-value is a replacement)
    """
    content = read_file(file__in)
    for k in replacements:
        content = content.replace(k, replacements[k])

    logging.info(f"$ cat {file_out}\n{content}")

    write_file(file_out, content)

def exec_cmd(command,template,substitutions):
    """
    Create a temprary file from template replacing the key-value pairs in
    substitutions and running the given command
    :param command:            Command to execute
    :param template:           Path to the template
    :param substitutions:      Dictionary of the replacements (each key-value is a replacement)
    """
    path_to_template = os.path.join(constants.TEMPLATES_DIR, template)
    path_to_tmp_file = os.path.join(constants.TEMPORARY_DIR, template)
    create_file_from_template(file__in=path_to_template,
                              file_out=path_to_tmp_file,
                              replacements=substitutions)
    cmd = command.format(path_to_tmp_file, constants.KUBECONFIG_PATH)
    return execute_command(command=cmd)

def kubectl_apply(template,substitutions):
    """
    Create a temprary file from template replacing the key-value pairs in
    substitutions and running the command "kubectl apply"
    :param template:          Path to the template
    :param substitutions:     Dictionary of the replacements (each key-value is a replacement)
    """
    exec_cmd(constants.COMMAND_KUBECTL_APPLY, template, substitutions)

def get_aws_ecr_registry_id():
    """
    Fetch the ID of the Registry from ECR (use boto3 client)
    :return The RegistryId
    """
    client = boto3.client('ecr')
    data = client.describe_registry()
    return data['registryId']


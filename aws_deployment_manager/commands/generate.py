"""This module handles site values file interaction."""
import logging
import os
import json
from aws_deployment_manager import constants, utils
from aws_deployment_manager.aws.aws_cfclient import AwsCFClient


LOG = logging.getLogger(__name__)


class GenerateManager():
    """ Main Class for generate Command """
    def __init__(self, env_name, region):
        self.env_name = env_name
        self.region = region
        self.config = {constants.AWS_REGION: region}
        self.aws_cfclient = AwsCFClient(config=self.config)

    def generate_config_file(self):
        """
        Generate IDUN Configuration file from existing IDUN deployment
        """
        config_file_path = constants.CONFIG_FILE_PATH
        LOG.info("Generating Config File at {0}".format(config_file_path))
        if os.path.exists(config_file_path):
            msg = "IDUN config file {0} already exists so it will not be overridden. Backup and rename the file " \
                  "and try again".format(config_file_path)
            LOG.error(msg)
            raise Exception(msg)

        LOG.info("IDUN config file {0} does not exist".format(config_file_path))

        idun_stack_name = self.env_name
        LOG.info("IDUN Stack Name = {0}".format(idun_stack_name))

        LOG.info("Getting stack parameters...")
        stack_details = self.aws_cfclient.get_stack_details(idun_stack_name)
        parameters = utils.get_stack_parameters(stack_details=stack_details)
        LOG.info("Stack parameters fetched. Preparing configuration object...")

        idun_deployment_config = {}
        idun_deployment_config[constants.ENVIRONMENT_NAME] = str(parameters[constants.ENVIRONMENT_NAME])
        idun_deployment_config[constants.AWS_REGION] = str(self.region)
        idun_deployment_config[constants.VPC_ID] = str(parameters[constants.VPC_ID])
        idun_deployment_config[constants.CONTROL_PLANE_SUBNET_IDS] = str(parameters[constants.CONTROL_PLANE_SUBNET_IDS])

        num_worker_node_subnets = parameters[constants.NUMBER_PRIVATE_SUBNETS]
        worker_node_subnet_ids = parameters[constants.PRIVATE_SUBNET_01_ID]
        if num_worker_node_subnets == 2:
            worker_node_subnet_ids = ",".join([parameters[constants.PRIVATE_SUBNET_01_ID],
                                               parameters[constants.PRIVATE_SUBNET_02_ID]])

        idun_deployment_config[constants.WORKER_NODE_SUBNET_IDS] = str(worker_node_subnet_ids)
        idun_deployment_config[constants.SECONDARY_VPC_CIDR] = str(parameters[constants.SECONDARY_VPC_CIDR])
        idun_deployment_config[constants.NODE_INSTANCE_TYPE] = str(parameters[constants.NODE_INSTANCE_TYPE])
        idun_deployment_config[constants.DISK_SIZE] = int(parameters[constants.DISK_SIZE])
        idun_deployment_config[constants.MIN_NODES] = int(parameters[constants.MIN_NODES])
        idun_deployment_config[constants.MAX_NODES] = int(parameters[constants.MAX_NODES])
        idun_deployment_config[constants.SSH_KEY_PAIR_NAME] = str(parameters[constants.SSH_KEY_PAIR_NAME])
        idun_deployment_config[constants.PRIVATE_DOMAIN_NAME] = str(parameters[constants.PRIVATE_DOMAIN_NAME])
        idun_deployment_config[constants.K8S_VERSION] = str(parameters[constants.K8S_VERSION])
        idun_deployment_config[constants.KUBE_DOWNSCALER] = bool(parameters[constants.KUBE_DOWNSCALER])
        idun_deployment_config[constants.BACKUP_INSTANCE_TYPE] = str(parameters[constants.BACKUP_INSTANCE_TYPE])
        idun_deployment_config[constants.BACKUP_AMI_ID] = str(parameters[constants.BACKUP_AMI_ID])
        idun_deployment_config[constants.BACKUP_DISK] = int(parameters[constants.BACKUP_DISK])
        idun_deployment_config[constants.BACKUP_PASS] = str(parameters[constants.BACKUP_PASS])

        hostnames = str(parameters[constants.HOSTNAMES]).replace('\'', '\"')
        hostnames_dict = json.loads(hostnames)
        idun_deployment_config[constants.HOSTNAMES] = hostnames_dict

        LOG.info("Writing configuration to file {0}".format(config_file_path))
        LOG.info(idun_deployment_config)
        # Write configuration into file
        utils.write_yaml(file_path=config_file_path,
                                config_parameters=idun_deployment_config)

        LOG.info("IDUN Configuration file genefrated at {0}".format(config_file_path))

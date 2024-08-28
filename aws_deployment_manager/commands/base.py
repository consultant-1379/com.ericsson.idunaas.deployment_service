"""
This module acts as base class for commands and contains common functions
"""
import logging
import os
import datetime
import re
import string
import random

import urllib.error
import wget

from aws_deployment_manager.aws.aws_s3client import AwsS3Client
from aws_deployment_manager.aws.aws_cfclient import AwsCFClient
from aws_deployment_manager.aws.aws_ec2client import AwsEC2Client
from aws_deployment_manager.aws.aws_r53client import AwsR53Client
from aws_deployment_manager.aws.aws_iamclient import AwsIAMClient
from aws_deployment_manager.aws.aws_eksclient import AwsEKSClient
from aws_deployment_manager.aws.aws_asgclient import AwsASGClient
from aws_deployment_manager import utils
from aws_deployment_manager import constants
from aws_deployment_manager import stagelog

LOG = logging.getLogger(__name__)


class Base:
    """ Base Class containing common functions for commands"""
    def __init__(self):
        self.cfout = dict()

        LOG.info("Loading IDUN Input Configuration File...")
        self.config = utils.load_yaml(file_path=constants.CONFIG_FILE_PATH)
        LOG.info(self.config)

        LOG.info("Validating IDUN Input Configuration File...")
        configuration_valid, validation_errors = utils.validate_idun_config(config=self.config)

        LOG.info("================================================================================================")
        if not configuration_valid:
            LOG.error("Configuration File not valid. {0} errors found".format(len(validation_errors)))
            for error in validation_errors:
                LOG.error(error)
            raise Exception("Configuration File is not valid")

        LOG.info("Configuration File valid. 0 errors found")
        LOG.info("================================================================================================")

        # Initialize AWS Clients
        self.aws_s3client = AwsS3Client(config=self.config)
        self.aws_cfclient = AwsCFClient(config=self.config)
        self.aws_ec2client = AwsEC2Client(config=self.config)
        self.aws_r53client = AwsR53Client(config=self.config)
        self.aws_iamclient = AwsIAMClient(config=self.config)
        self.aws_eksclient = AwsEKSClient(config=self.config)
        self.aws_asgclient = AwsASGClient(config=self.config)

        # Store Variables from Configuration
        self.aws_region = self.config[constants.AWS_REGION]
        self.environment_name = self.config[constants.ENVIRONMENT_NAME]
        self.vpcid = self.config[constants.VPC_ID]

        worker_node_subnet_ids = str(self.config[constants.WORKER_NODE_SUBNET_IDS]).split(",")
        self.num_of_subnets = len(worker_node_subnet_ids)
        self.worker_node_subnet_01_id = worker_node_subnet_ids[0]
        if self.num_of_subnets == 2:
            self.worker_node_subnet_02_id = worker_node_subnet_ids[1]

        self.control_plane_subnet_ids = str(self.config[constants.CONTROL_PLANE_SUBNET_IDS])
        temp = self.control_plane_subnet_ids.split(",")
        self.control_plane_subnet_01_id = temp[0]
        self.control_plane_subnet_02_id = temp[1]
        self.min_nodes = self.config[constants.MIN_NODES]
        self.disk_size = self.config[constants.DISK_SIZE]
        self.max_nodes = self.config[constants.MAX_NODES]
        self.secondary_vpc_cidr = self.config[constants.SECONDARY_VPC_CIDR]
        self.instance_type = self.config[constants.NODE_INSTANCE_TYPE]
        self.disable_public_access = self.config[constants.DISABLE_PUBLIC_ACCESS]
        self.is_ecn_connected = self.disable_public_access
        self.infra_master_stack_name = self.environment_name
        self.infra_add_stack_name = self.environment_name + constants.IDUN_ADDITIONAL_SUFFIX_STACK_NAME
        self.alb_controller_stack_name = self.environment_name + constants.ALB_CONTROLLER_SUFFIX_STACK_NAME
        self.csi_controller_stack_name = self.environment_name + constants.CSI_CONTROLLER_SUFFIX_STACK_NAME
        self.ssh_key_pair_name = self.config[constants.SSH_KEY_PAIR_NAME]
        self.k8sversion = self.config[constants.K8S_VERSION]
        self.kube_downscaler = self.config[constants.KUBE_DOWNSCALER]
        self.backup_disk = self.config[constants.BACKUP_DISK]
        self.backup_ami = self.config[constants.BACKUP_AMI_ID]
        self.backup_instance_type = self.config[constants.BACKUP_INSTANCE_TYPE]
        self.backup_pass = self.config[constants.BACKUP_PASS]
        self.ingest_service_account_name = constants.INGEST_SA_NAME__DEFUALT


        # Get Primary VPC CIDR
        self.primary_vpc_cidr = self.aws_ec2client.get_primary_cidr(vpcid=self.vpcid)

        # Get Availability Zones for Private Subnets
        self.control_plane_subnet_01_az = self.aws_ec2client.get_subnet_availability_zone(
            subnet_id=self.control_plane_subnet_01_id)
        self.control_plane_subnet_02_az = self.aws_ec2client.get_subnet_availability_zone(
            subnet_id=self.control_plane_subnet_02_id)

        self.worker_node_subnet_01_az = self.aws_ec2client.get_subnet_availability_zone(
            subnet_id=self.worker_node_subnet_01_id)
        if self.num_of_subnets == 2:
            self.worker_node_subnet_02_az = self.aws_ec2client.get_subnet_availability_zone(
                subnet_id=self.worker_node_subnet_02_id)

        # Get Route Table IDs for Private Subnets
        self.control_plane_subnet_rt_01_id = self.aws_ec2client.get_route_table_ids(
            subnet_id=self.control_plane_subnet_01_id)
        self.control_plane_subnet_rt_02_id = self.aws_ec2client.get_route_table_ids(
            subnet_id=self.control_plane_subnet_02_id)

        self.worker_node_subnet_rt_01_id = self.aws_ec2client.get_route_table_ids(
            subnet_id=self.worker_node_subnet_01_id)
        if self.num_of_subnets == 2:
            self.worker_node_subnet_rt_02_id = self.aws_ec2client.get_route_table_ids(
                subnet_id=self.worker_node_subnet_02_id)

        # Get Hostnamess from Config
        self.hosted_zone_name = str(self.config[constants.PRIVATE_DOMAIN_NAME])
        self.hostnames = []
        if constants.HOSTNAMES in self.config:
            hostnames = self.config[constants.HOSTNAMES]
            for host in hostnames:
                self.hostnames.append(hostnames[host])


        # Create S3 bucket for storing templates
        self.bucket_name = str(self.config[constants.ENVIRONMENT_NAME]).lower() + constants.BUCKET_POSTFIX
        self.s3_endpoint = self.aws_s3client.create_bucket(bucket_name=self.bucket_name)
        self.s3_url = self.s3_endpoint + constants.VERSION
        self.template_urls = {}
        LOG.info("S3 Bucket URL - {0}".format(self.s3_url))
        self.stage_log_path = ""
        self.all_stages = {}
        self.outputs = {}
        self.cluster_name = ""

        # Load Version Mappings
        eks_versions_template = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_EKS_VERSIONS)
        eks_versions = utils.load_yaml(file_path=eks_versions_template)

        self.kube_proxy_version = eks_versions[self.k8sversion][constants.KUBE_PROXY]
        self.core_dns_version = eks_versions[self.k8sversion][constants.CORE_DNS]
        self.cni_plugin_version = eks_versions[self.k8sversion][constants.CNI_PLUGIN]
        self.auto_scaler_version = eks_versions[self.k8sversion][constants.AUTO_SCALER]
        self.aws_lb_controller_version = eks_versions[self.k8sversion][constants.AWS_LB_CONTROLLER]

        LOG.info("Add On Kube Proxy Version = {0}".format(self.kube_proxy_version))
        LOG.info("Add On Core DNS Version = {0}".format(self.core_dns_version))
        LOG.info("Add On Custom CNI Version = {0}".format(self.cni_plugin_version))
        LOG.info("Add On Auto Scaler Version = {0}".format(self.auto_scaler_version))
        LOG.info("Add On AWS Loadbalancer controller Version = {0}".format(self.aws_lb_controller_version))

        LOG.info("Add Docker Registries")
        if self.disable_public_access is False: # Public Account (not ECN connected)
            self.registry_map = self._get_aws_registry_map()
        else: # ECN connected
            self.registry_map = self._get_ecn_registry_map()

    def _get_ecn_registry_map(self):
        return dict(
            CALICO_OP_REGISTRY             = constants.ARMDOCKER_RND,
            CALICO_CRS_REGISTRY            = constants.ARMDOCKER_RND+"/dockerhub-ericsson-remote",
            NGX_CTR_REGISTRY               = constants.ARMDOCKER_RND,
            CLUSTER_AUTOS_REGISTRY         = constants.ARMDOCKER_GIC,
            CLUSTER_AUTOS_VERSION          = 'v' + self.auto_scaler_version,
            K8s_DOWNS_REGISTRY             = constants.ARMDOCKER_GIC,
            PROM_CFGMAP_REGISTRY           = constants.EIAPAAS_REGISTRY,
            PROM_KSTMTR_REGISTRY           = constants.EIAPAAS_REGISTRY,
            PROM_NODE_EXPORTER_REGISTRY    = constants.EIAPAAS_REGISTRY,
            PROM_PUSHGATEWAY_REGISTRY      = constants.EIAPAAS_REGISTRY,
            PROM_SERVER_REGISTRY           = constants.EIAPAAS_REGISTRY,
            METRICS_REGISTRY               = constants.ARMDOCKER_GIC,
            K8S_DASH_REGISTRY              = constants.ARMDOCKER_GIC,
            EXTRA_CALICO_CTRL_REGISTRY     = constants.ARMDOCKER_RND,
            EXTRA_CALICO_OTHER_REGISTRY    = constants.ARMDOCKER_GIC,
            EXTRA_EIAP_PROJ_REGISTRY       = constants.ARMDOCKER_GIC,
            EBS_CSI_REGISTRY               = constants.EIAPAAS_REGISTRY
        )

    def _get_aws_registry_map(self):
        # AWS_ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        registry_id = utils.get_aws_ecr_registry_id()
        AWS_ECR_URL=f"{registry_id}.dkr.ecr.{self.aws_region}.amazonaws.com"
        self.aws_ecr_registry = AWS_ECR_URL
        return dict(
            CALICO_OP_REGISTRY             = AWS_ECR_URL,
            CALICO_CRS_REGISTRY            = AWS_ECR_URL,
            NGX_CTR_REGISTRY               = AWS_ECR_URL,
            CLUSTER_AUTOS_REGISTRY         = AWS_ECR_URL,
            CLUSTER_AUTOS_VERSION          = 'v' + self.auto_scaler_version,
            K8s_DOWNS_REGISTRY             = AWS_ECR_URL,
            PROM_CFGMAP_REGISTRY           = AWS_ECR_URL,
            PROM_KSTMTR_REGISTRY           = AWS_ECR_URL,
            PROM_NODE_EXPORTER_REGISTRY    = AWS_ECR_URL,
            PROM_PUSHGATEWAY_REGISTRY      = AWS_ECR_URL,
            PROM_SERVER_REGISTRY           = AWS_ECR_URL,
            METRICS_REGISTRY               = AWS_ECR_URL,
            K8S_DASH_REGISTRY              = AWS_ECR_URL,
            EXTRA_CALICO_CTRL_REGISTRY     = AWS_ECR_URL,
            EXTRA_CALICO_OTHER_REGISTRY    = AWS_ECR_URL,
            EXTRA_EIAP_PROJ_REGISTRY       = AWS_ECR_URL,
            EBS_CSI_REGISTRY               = AWS_ECR_URL
        )

    def load_stage_states(self, stage_log_path):
        """
        Load all install stages executed from stage log file
        :param stage_log_path: Path to install stage log file
        :return: Dict with stage name and state (started/finished)
        """
        self.stage_log_path = stage_log_path
        self.all_stages = stagelog.get_all_stages(log_path=self.stage_log_path)

    def upload_templates(self):
        """
        Upload Cloudformation Templates to S3 Bucket
        """
        LOG.info("Uploading Template files to bucket {0}".format(self.s3_url))
        for item in os.listdir(constants.TEMPLATES_DIR):
            LOG.info("Uploading {0} template to S3".format(item))
            filepath = os.path.join(constants.TEMPLATES_DIR, item)
            key = constants.VERSION + "/" + item
            url = self.aws_s3client.put_object(filepath=filepath, key=key, bucket_name=self.bucket_name)
            self.template_urls[item] = url
            LOG.info("SUCCESS - Uploaded {0} template to S3".format(key))

        LOG.info("SUCCESS - Uploaded Template files to bucket {0}".format(self.s3_url))

    def get_config_parameters_for_idun_cf_stack(self):
        """
        Get Configuration Parameters to be passed to CF for Stack Creation of IDUN
        :return: Configuration Parameters Dictionary
        """
        # Prepare Template Parameters Object
        config_parameters = {}
        config_parameters[constants.VPC_ID] = str(self.vpcid)
        config_parameters[constants.NUMBER_PRIVATE_SUBNETS] = str(self.num_of_subnets)
        config_parameters[constants.PRIVATE_SUBNET_01_ID] = str(self.worker_node_subnet_01_id)
        config_parameters[constants.PRIVATE_SUBNET_01_AZ] = str(self.worker_node_subnet_01_az)

        if self.num_of_subnets == 2:
            config_parameters[constants.PRIVATE_SUBNET_02_ID] = str(self.worker_node_subnet_02_id)
            config_parameters[constants.PRIVATE_SUBNET_02_AZ] = str(self.worker_node_subnet_02_az)
        else:
            config_parameters[constants.PRIVATE_SUBNET_02_ID] = "NA"
            config_parameters[constants.PRIVATE_SUBNET_02_AZ] = "NA"

        config_parameters[constants.CONTROL_PLANE_SUBNET_IDS] = str(self.control_plane_subnet_ids)
        config_parameters[constants.ENVIRONMENT_NAME] = str(self.environment_name)
        config_parameters[constants.PRIMARY_VPC_CIDR] = str(self.primary_vpc_cidr)
        config_parameters[constants.SECONDARY_VPC_CIDR] = str(self.secondary_vpc_cidr)
        config_parameters[constants.S3_URL] = str(self.s3_url)
        config_parameters[constants.NODE_INSTANCE_TYPE] = str(self.instance_type)
        config_parameters[constants.DISK_SIZE] = str(self.disk_size)
        config_parameters[constants.MIN_NODES] = str(self.min_nodes)
        config_parameters[constants.MAX_NODES] = str(self.max_nodes)
        config_parameters[constants.SSH_KEY_PAIR_NAME] = str(self.ssh_key_pair_name)
        config_parameters[constants.PRIVATE_DOMAIN_NAME] = str(self.hosted_zone_name)
        config_parameters[constants.K8S_VERSION] = str(self.k8sversion)
        config_parameters[constants.DISABLE_PUBLIC_ACCESS] = str(self.disable_public_access)
        config_parameters[constants.KUBE_DOWNSCALER] = str(self.kube_downscaler)
        config_parameters[constants.AWS_REGION] = str(self.aws_region)

        #config_parameters[constants.BACKUP_DISK] = str(self.backup_disk)
        #config_parameters[constants.BACKUP_INSTANCE_TYPE] = str(self.backup_instance_type)
        #config_parameters[constants.BACKUP_AMI_ID] = str(self.backup_ami)
        #config_parameters[constants.BACKUP_PASS] = str(self.backup_pass)

        hostnames = {}
        for host in self.config[constants.HOSTNAMES]:
            hostnames[host] = self.config[constants.HOSTNAMES][host]
        config_parameters[constants.HOSTNAMES] = str(hostnames)

        self.__show_cf_config_parameters(config_parameters)
        return config_parameters

    def __get_infra_add_config_parameters(self):
        """The input parameters for the cloudformation stack"""
        config_parameters = {}
        config_parameters[constants.ENVIRONMENT_NAME] = self.environment_name
        config_parameters[constants.EKS_CLUSTER_OIDC] = self.cfout[self.infra_master_stack_name][constants.EKS_CLUSTER_OIDC]
        config_parameters[constants.SERVICE_ACCOUNT_NAMESPACE] = constants.PROM_NAMESPACE
        config_parameters[constants.INGEST_SERVICE_ACCOUNT_NAME] = self.ingest_service_account_name
        return config_parameters

    def get_config_parameters_for_alb_cf_stack(self):
        """
        Get Configuration Parameters to be passed to CF for Stack Creation of ALB Controller
        for AWS Policy and AWS Role
        :return: Configuration Parameters Dictionary
        """
        # Prepare Template Parameters Object
        config_parameters = {}
        config_parameters[constants.ENVIRONMENT_NAME] = str(self.environment_name)
        config_parameters[constants.AWS_REGION] = str(self.aws_region)
        config_parameters[constants.EKS_CLUSTER_OIDC] = str(self.outputs[constants.EKS_CLUSTER_OIDC])
        self.__show_cf_config_parameters(config_parameters)
        return config_parameters

    def get_config_parameters_for_csi_cf_stack(self):
        """
        Get Configuration Parameters to be passed to CF for Stack Creation of ALB Controller
        for AWS Policy and AWS Role
        :return: Configuration Parameters Dictionary
        """
        # Prepare Template Parameters Object
        config_parameters = {}
        config_parameters[constants.ENVIRONMENT_NAME] = self.environment_name
        config_parameters[constants.AWS_REGION] = self.aws_region
        config_parameters[constants.EKS_CLUSTER_OIDC] = self.cfout[self.infra_master_stack_name][constants.EKS_CLUSTER_OIDC]
        config_parameters[constants.EBS_KMS_KEY_ARN] = self.cfout[self.infra_master_stack_name][constants.EBS_KMS_KEY_ARN]
        self.__show_cf_config_parameters(config_parameters)
        return config_parameters

    def __show_cf_config_parameters(self, config_parameters):
        LOG.info("Template Parameters...")
        for param in config_parameters:
            LOG.info("{0} - {1}".format(param, config_parameters[param]))

    def get_base_vpc_config_parameters(self):
        """
        Get Configuration Parameters to be passed to CF for Base VPC Stack Creation
        :return: Configuration Parameters Dictionary
        """
        # Prepare Template Parameters Object
        config_parameters = {}
        config_parameters[constants.VPC_ID] = str(self.vpcid)
        config_parameters[constants.PRIVATE_SUBNET_01_ID] = str(self.control_plane_subnet_01_id)
        config_parameters[constants.PRIVATE_SUBNET_02_ID] = str(self.control_plane_subnet_02_id)
        config_parameters[constants.PRIVATE_SUBNET_01_RT_ID] = str(self.control_plane_subnet_rt_01_id)
        config_parameters[constants.PRIVATE_SUBNET_02_RT_ID] = str(self.control_plane_subnet_rt_02_id)
        config_parameters[constants.ENVIRONMENT_NAME] = str(self.environment_name)
        config_parameters[constants.PRIMARY_VPC_CIDR] = str(self.primary_vpc_cidr)

        LOG.info("Template Parameters...")
        for param in config_parameters:
            LOG.info("{0} - {1}".format(param, config_parameters[param]))
        return config_parameters

    def get_idun_stack_outputs(self):
        """
        Get IDUN Stack Outputs
        :return: Stack Outputs as Dictionary
        """

        return self.get_cf_stack_outputs(self.infra_master_stack_name)

    def get_cf_stack_outputs(self, stack_name):
        """
        Get VPC Stack Outputs
        :return: Stack Outputs as Dictionary
        """
        outputs = dict()
        if self.aws_cfclient.stack_exists(stack_name):
            stack_details = self.aws_cfclient.get_stack_details(stack_name)
            outputs = utils.get_stack_outputs(stack_details)
            LOG.debug('Stack {} Details: {} Output: {}'.format(stack_name, stack_details, outputs))
        else:
            LOG.warn("Stack {} does not exists".format(stack_name))

        return outputs

    def stage_executed(self, stage):
        """
        Checks if a stage has been executed
        :param stage: Name of stage
        :return: True if stage has been executed else False
        """
        stage_executed = False

        # Check if stage exists in stage Map
        if stage in self.all_stages:
            # Get state of stage
            state = self.all_stages[stage]
            # If state is finished, then stage has been executed
            if state == constants.STAGE_FINISHED:
                stage_executed = True

        return stage_executed

    def update_stage_state(self, stage, state):
        """
        Updates state of a stage in stage log
        :param stage: Name of stage
        :param state: State of stage (started/finished)
        """

        stagelog.write_to_stage_log(log_path=self.stage_log_path,
                                    stage=stage,
                                    state=state)

    def execute_stage(self, func, stage):
        """
        Execute a stage
        :param func: Name of function
        :param stage: Name of stage
        """
        if self.stage_executed(stage=stage):
            LOG.info("Skipping stage {0}".format(stage))
            return

        LOG.info("*************************************************")
        LOG.info("Started Executing stage {0}".format(stage))
        LOG.info("*************************************************")
        self.update_stage_state(stage=stage, state=constants.STAGE_STARTED)

        # Execute the function
        func()

        LOG.info("*************************************************")
        LOG.info("Finished Executing stage {0}".format(stage))
        LOG.info("*************************************************")
        self.update_stage_state(stage=stage, state=constants.STAGE_FINISHED)

    def create_node_group(self, desired_size=None):
        """
        Create Node Group in EKS Cluster
        :param desired_size: Desired number of nodes in Node Group
        :return: Name of Node Group
        """
        if desired_size is None:
            desired_size = self.min_nodes
        current_date = datetime.datetime.now()
        current_day = current_date.strftime("%Y%m%d")
        random_string = ''.join(random.choices(string.ascii_uppercase, k=5))
        nodegroup_name = constants.NODEGROUP_NAME.format(self.cluster_name, current_day, random_string)
        subnets = [self.worker_node_subnet_01_id]

        if self.num_of_subnets == 2:
            subnets.append(self.worker_node_subnet_02_id)

        self.aws_eksclient.create_nodegroup(cluster_name=self.cluster_name,
                                            nodegroup_name=nodegroup_name,
                                            min_size=int(self.min_nodes),
                                            max_size=int(self.max_nodes),
                                            desired_size=desired_size,
                                            disk_size=int(self.disk_size),
                                            subnets=subnets,
                                            instance_type=self.instance_type,
                                            ami_type=constants.AMI_TYPE,
                                            node_role=self.outputs[constants.NODE_ROLE_ARN],
                                            ec2_ssh_keypair_name=self.ssh_key_pair_name)
        return nodegroup_name

    def get_sso_admin_role_name(self):
        """
        Gets SSO Consumer Admin Role Name
        :return: Role Name
        """
        roles = self.aws_iamclient.list_roles(env_name=self.environment_name)
        for role in roles:
            role_name = str(role['RoleName'])
            if 'AWSReservedSSO_SSO-Consumer-admin' in role_name:
                return role_name

        raise Exception("Could not get role name for SSO Consumer Admin")

    def enable_cluster_auto_scaler(self):
        """
        Start Cluster Auto Scaler
        """
        LOG.info("Enabling Cluster Auto Scaler for {0}".format(self.environment_name))
        command = constants.COMMAND_START_CLUSTER_AUTOSCALER.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

    def disable_cluster_auto_scaler(self):
        """
        Stop Cluster Auto Scaler
        """
        LOG.info("Disabling Cluster Auto Scaler for {0}".format(self.environment_name))
        command = constants.COMMAND_STOP_CLUSTER_AUTOSCALER.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

    def update_cni_plugin(self):
        """
        Update the CNI Plugin during install and upgrade
        """
        LOG.info("Updating CNI Plugin...")
        file = "aws-k8s-cni.yaml"
        url = f"https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v{self.cni_plugin_version}/config/master/aws" \
              f"-k8s-cni.yaml"
        try:
            wget.download(url, file)
        except urllib.error.HTTPError as error:
            LOG.error("Update CNI Plugin failed...Bad CNI version\n", error)
        else:
            region_old = 'us-west-2'
            region_new = self.aws_region

            with open(file, "r") as sources:
                lines = sources.readlines()
            with open(file, "w") as sources:
                for line in lines:
                    sources.write(re.sub(region_old, region_new, line))
            LOG.info("Applying CNI Plugin via manifest {0}".format(file))
            command = constants.COMMAND_KUBECTL_APPLY.format(file, constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            command = constants.COMMAND_ENABLE_CUSTOM_CNI_CONFIG.format(constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            LOG.info("Updated CNI Plugin")

    def install_or_upgrade_aws_lb_controller(self):
        """
        Install AWS LB controller using Helm. In case it is already installed it will upgrade.
        """
        LOG.info("Updating aws loadbalancer controller help repo in {0}".format(self.cluster_name))
        LOG.info("Adding ALB controller Repo in Helm...")
        command = constants.COMMAND_ALB_CONTROLLER_REPO_ADD
        utils.execute_command(command=command)

        LOG.info("Installing/Updating aws loadbalancer controller in {0}".format(self.cluster_name))
        eks_cluster_name = self.outputs[constants.EKS_CLUSTER_NAME]
        command = constants.COMMAND_INSTALL_ALB_CONTROLLER.format(
            eks_cluster_name, self.aws_region, self.aws_lb_controller_version, constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)
        LOG.info("Installed/Upgraded aws loadbalancer controller in {0}".format(self.cluster_name))

    def create_or_update_idun_stack(self):
        """
        Create or Update AWS Cloudformation Stack for main infrastructure
        :return: Stack Update Response
        """
        return self.create_or_update_cf_stack(
                           stack_name=self.infra_master_stack_name,
                           template_name=constants.TEMPLATE_INFRA_MASTER,
                           config_parameters = self.get_config_parameters_for_idun_cf_stack()
                           )

    def create_or_update_idun_additional_stack(self):
        return self.create_or_update_cf_stack(
                               stack_name=self.infra_add_stack_name,
                               template_name=constants.TEMPLATE_INFRA_ADD,
                               config_parameters = self.__get_infra_add_config_parameters()
                               )

    def create_or_update_alb_controller_stack(self):
        """
        Create or Update ALB Controller Stack in AWS
        :return: Stack creation response from Cloudformation
        """
        return self.create_or_update_cf_stack(
                                    stack_name=self.alb_controller_stack_name,
                                    template_name=constants.TEMPLATE_ALB_CONTROLLER,
                                    config_parameters=self.get_config_parameters_for_alb_cf_stack()
                                )

    def create_or_update_csi_controller_stack(self):
        """
        Create or Update CSI Controller Stack in AWS
        :return: Stack creation response from Cloudformation
        """
        return self.create_or_update_cf_stack(
                                    stack_name=self.csi_controller_stack_name,
                                    template_name=constants.TEMPLATE_CSI_CONTROLLER,
                                    config_parameters=self.get_config_parameters_for_csi_cf_stack()
                                )

    def create_or_update_cf_stack(self, stack_name, template_name, config_parameters):
        """
        Internal method to create IDUN Stack in AWS
        :return: Stack creation response from Cloudformation
        """

        stack_func_args = dict(
                template_url=self.template_urls[template_name],
                stack_name=stack_name,
                template_name=template_name,
                config_parameters=config_parameters)

        LOG.info("Stack Name = {0}, Template = {1}".format(stack_name, stack_func_args['template_url']))
        LOG.debug("config_parameters = {}".format(config_parameters))

        # Check if stack already exists
        if self.aws_cfclient.stack_exists(stack_name=stack_name):
            LOG.info("Stack {0} already exists. Trying to update the stack...".format(stack_name))
            response = self.aws_cfclient.update_stack(**stack_func_args)
        else:
            LOG.info("Stack {0} does not exist. Creating stack...".format(stack_name))
            response = self.aws_cfclient.create_stack(**stack_func_args)

        self.cfout[stack_name] = self.get_cf_stack_outputs(stack_name)

        return response

    def install_or_upgrade_kube_downscaler(self):
        """
        Deploy Kube-downscaler app
        """
        if self.config[constants.KUBE_DOWNSCALER]:
            LOG.info("Deploying Kube-downscaler app in EKS Cluster {0}".format(self.cluster_name))
            utils.kubectl_apply(constants.TEMPLATE_KUBE_DOWNSCALER,self.registry_map)

            LOG.info("Deployed Kube-downscaler app")
        else:
            LOG.info("Skipping  Kube-downscaler app deployment")

    def deploy_ebs_csi_controller(self):
        """
        Deploy AWS EBS CSI Controller
        """
        LOG.info("Deploying AWS EBS CSI Controller in EKS Cluster {0}".format(self.cluster_name))

        LOG.info("Adding AWs EBS CSI Controller Repo in Helm...")
        utils.execute_command(command=constants.CSI_HELM_REPO_ADD)

        # Install AWS EBS CSI Controller
        LOG.info("Installing AWS EBS CSI Controller...")
        subs = {
            "CSI_CONTROLLER_ROLE_ARN": self.cfout[self.csi_controller_stack_name][constants.CSI_CONTROLLER_ROLE_ARN],
            **self.registry_map
        }
        utils.exec_cmd(constants.CSI_HELM_UPGRADE_INSTALL,constants.TEMPLATE_CSI_VALUES,subs)

        # Create Storage Class
        utils.kubectl_apply(constants.TEMPLATE_GP3_STORAGE_CLASS,
            dict(KMS_KEY_ARN=self.cfout[self.infra_master_stack_name][constants.EBS_KMS_KEY_ARN]))

        LOG.info("Deployed AWS EBS CSI Controller")

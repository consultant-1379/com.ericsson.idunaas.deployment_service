"""
This module implements Install command
"""
import logging
import os
import time
from packaging.version import Version
from aws_deployment_manager.commands.base import Base
from aws_deployment_manager import utils
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class InstallManager(Base):
    """ Main Class for Install command """
    def __init__(self, armdocker_user, armdocker_pass):
        Base.__init__(self)
        self.load_stage_states(stage_log_path=constants.INSTALL_STAGE_LOG_PATH)
        self.__armdocker_user = armdocker_user
        self.__armdocker_pass = armdocker_pass

    def pre_install(self):
        """
        IDUN Pre-Install Steps
        """
        LOG.info("Executing Pre-Install Steps...")

        # Apply EKS Tags to Private Subnets in VPC
        self.execute_stage(func=self._apply_eks_tags_to_subnets,
                           stage=constants.INSTALL_STAGE_APPLY_EKS_TAGS)

        LOG.info("Pre Install Done")

    def install(self):
        """
        IDUN Install Steps
        """
        try:
            LOG.info("Installing IDUN AWS for {0}".format(self.environment_name))

            # Upload Template URLs to S3 Bucket
            self.upload_templates()

            # Create IDUN Base VPC Stack
            self.execute_stage(func=self._create_base_vpc_stack,
                               stage=constants.INSTALL_STAGE_CREATE_BASE_VPC_STACK)

            # Update Endpoint Security Group
            self.execute_stage(func=self._update_endpoint_security_group,
                               stage=constants.INSTALL_STAGE_UPDATE_ENDPOINT_SEC_GR)

            if not self.is_ecn_connected:
                # Create IDUN Base Additional Resources Stack
                self.execute_stage(func=self._create_base_additional_stack,
                       stage=constants.INSTALL_STAGE_CREATE_BASE_ADD_STACK)

            # Create IDUN Stack
            self.execute_stage(func=self.create_or_update_idun_stack,
                               stage=constants.INSTALL_STAGE_CREATE_IDUN_INFRA_STACK)

            if not self.is_ecn_connected:
                # Create IDUN Infrastructure Additional Resources Stack
                self.execute_stage(func=self.create_or_update_idun_additional_stack,
                       stage=constants.INSTALL_STAGE_CREATE_IDUN_ADDIT_STACK)

            # Get IDUN Stack Output
            self.outputs = self.get_idun_stack_outputs()
            self.cluster_name = str(self.outputs[constants.EKS_CLUSTER_NAME])

            # Create IDUN ALB Controller Stack
            self.execute_stage(func=self.create_or_update_alb_controller_stack,
                               stage=constants.INSTALL_STAGE_CREATE_ALB_CONTROLLER_STACK)

            if Version(self.k8sversion) > Version('1.22'):
                # Create IDUN CSI Controller Stack
                self.execute_stage(func=self.create_or_update_csi_controller_stack,
                                   stage=constants.INSTALL_STAGE_CREATE_CSI_CONTROLLER_STACK)

            # Generate Kube Config for Admin User
            self._generate_kube_config_for_admin()

            LOG.info("Waiting for EKS Control Plane to come up properly...")
            time.sleep(30)

            # Update Config Map with SAML Admin Role
            self.execute_stage(func=self._update_k8s_config_map,
                               stage=constants.INSTALL_STAGE_UPDATE_K8S_CONFIG_MAP)

            # Enable Private Endpoint Access for EKS Cluster
            self.execute_stage(func=self._change_cluster_private_public_access,
                               stage=constants.INSTALL_STAGE_CHANGE_CLUSTER_ACCESS)

            # Update CNI Version
            self.execute_stage(func=self.update_cni_plugin,
                               stage=constants.INSTALL_STAGE_UPDATE_CNI_VERSION)

            # Enable Custom CNI Config
            self.execute_stage(func=self._enable_custom_cni_config,
                               stage=constants.INSTALL_STAGE_ENABLE_CNI_CONFIG)

            # Create and Apply ENI Config files for POD Subnets
            self.execute_stage(func=self._create_eni_config,
                               stage=constants.INSTALL_STAGE_CREATE_ENI_CONFIG)

            # Update ENI Config Label
            self.execute_stage(func=self._set_eni_config_label,
                               stage=constants.INSTALL_STAGE_SET_ENI_LABEL)

            # Deploy Calico CNI
            self.execute_stage(func=self._deploy_calico,
                               stage=constants.INSTALL_STAGE_DEPLOY_CALICO_CNI)

            self._delete_storage_class(constants.STORAGE_CLASS_NAME_GP2)
            self._delete_storage_class(constants.STORAGE_CLASS_NAME_GP3)
            if Version(self.k8sversion) > Version('1.22'):
                # Deploy EBS CSI Controller
                self.execute_stage(func=self.deploy_ebs_csi_controller,
                                   stage=constants.INSTALL_STAGE_DEPLOY_EBS_CSI_CONTROLLER)
            else:
                # Create GP2 Default Storage Class
                self.execute_stage(func=self._create_gp2_storage_class,
                                   stage=constants.INSTALL_STAGE_CREATE_DEFAULT_STORAGE)

            # Create Node Group
            self.execute_stage(func=self.create_node_group,
                               stage=constants.INSTALL_STAGE_CREATE_NODE_GROUP)

            LOG.info("SUCCESS - Created IDUN AWS Stack")
        except Exception as exception:
            raise exception

    def post_install(self):
        """
        IDUN Post Install Steps
        """
        LOG.info("Executing Post Install Steps...")
        self.outputs = self.get_idun_stack_outputs()

        if constants.EKS_CLUSTER_NAME in self.outputs:
            # Create namespaces
            utils.create_namespace(namespace=constants.NAMESPACE_K8S_DASHBOARD)
            utils.create_namespace(namespace=constants.NAMESPACE_NGINX)
            utils.create_namespace(namespace=constants.NAMESPACE_KUBE_SYSTEM)

            # Create Armdocker Secret to pull images
            self._create_armdocker_secret(namespace=constants.NAMESPACE_K8S_DASHBOARD)
            self._create_armdocker_secret(namespace=constants.NAMESPACE_NGINX)
            self._create_armdocker_secret(namespace=constants.NAMESPACE_KUBE_SYSTEM)

            # Deploy K8S Dashbord
            self.execute_stage(func=self._setup_k8s_dashboard,
                               stage=constants.INSTALL_STAGE_SETUP_K8S_DASHBOARD)

            # Generate Kubeconfig files as output
            LOG.info("K8S Config File generated at {0}".format(constants.KUBECONFIG_PATH))

            LOG.info("Post Install done")
        else:
            raise Exception("Failed to execute Post Install steps. Not able to get Cluster Name from Stack Output. "
                            "Stack Name is {0}".format(self.infra_master_stack_name))

    def get_config_files(self):
        """
        Generate KubeConfig file for IDUN Deployment
        :return: Path to K8S KubeConfig File
        """
        LOG.info("Generating K8S Config File for {0}".format(self.environment_name))
        self.outputs = self.get_idun_stack_outputs()

        if constants.EKS_CLUSTER_NAME in self.outputs:
            # Generate Kube Config for Admin User
            self._generate_kube_config_for_admin()

            # Generate Kubeconfig files as output
            LOG.info("K8S Config File generated at {0}".format(constants.KUBECONFIG_PATH))
            return constants.KUBECONFIG_PATH

        raise Exception("Failed to generate config files. Not able to get Cluster Name from Stack Output. "
                        "Stack Name is {0}".format(self.infra_master_stack_name))

    def _create_base_vpc_stack(self):
        return self.create_or_update_cf_stack(
                               stack_name=constants.BASE_VPC_STACK_NAME,
                               template_name=constants.TEMPLATE_BASE_VPC,
                               config_parameters = self.get_base_vpc_config_parameters()
                               )

    def _create_base_additional_stack(self):
        return self.create_or_update_cf_stack(
                               stack_name=constants.BASE_ADDITIONAL_STACK_NAME,
                               template_name=constants.TEMPLATE_BASE_ADDITIONAL,
                               config_parameters = self.__get_base_additional_config_parameters()
                               )

    def __get_base_additional_config_parameters(self):
        """The input parameters for the cloudformation stack"""
        config_parameters = {}
        config_parameters[constants.VPC_ID] = self.vpcid
        config_parameters[constants.PRIVATE_SUBNET_01_ID] = self.control_plane_subnet_01_id
        config_parameters[constants.PRIVATE_SUBNET_02_ID] = self.control_plane_subnet_02_id
        config_parameters[constants.ENDPOINT_SECURITY_GROUP_ID] = \
            self.cfout[constants.BASE_VPC_STACK_NAME][constants.ENDPOINT_SECURITY_GROUP_ID]
        return config_parameters

    def _get_cluster_config(self):
        """
        Get EKS Cluster Configuration
        :return: Cluster Configuration in JSON format
        """
        cluster_config = self.aws_eksclient.describe_cluster(cluster_name=self.cluster_name)
        return cluster_config

    def _change_cluster_private_public_access(self):
        """
        Change Public and Private access for EKS Control Plane
        """
        # First Get current Cluster Config
        cluster_config = self._get_cluster_config()

        endpoint_public_access = cluster_config['cluster']['resourcesVpcConfig']['endpointPublicAccess']
        endpoint_private_access = cluster_config['cluster']['resourcesVpcConfig']['endpointPrivateAccess']

        LOG.info("Public Endpoint for EKS Cluster enabled = {0}".format(endpoint_public_access))
        LOG.info("Private Endpoint for EKS Cluster enabled = {0}".format(endpoint_private_access))

        enable_private_access = True
        enable_public_access = True

        if self.disable_public_access is True:
            enable_public_access = False

        if (endpoint_public_access != enable_public_access) \
                or (endpoint_private_access != enable_private_access):
            LOG.info("Changing Access for EKS Cluster {0}, Public Access = {1}, Private Access = {2}"
                     .format(self.cluster_name, enable_public_access, enable_private_access))

            self.aws_eksclient.update_cluster_access_endpoints(cluster_name=self.cluster_name,
                                                               enable_public_access=enable_public_access,
                                                               enable_private_access=enable_private_access)

    def _enable_custom_cni_config(self):
        """
        Enable Custom ENI Config for POD Network in EKS
        """
        LOG.info("Enabling Custom ENI Config for EKS Cluster {0}".format(self.cluster_name))
        command = constants.COMMAND_ENABLE_CUSTOM_CNI_CONFIG.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)
        LOG.info("Enabled Custom ENI Config")

    def _set_eni_config_label(self):
        """
        Set ENI Config Label
        """
        LOG.info("Updating ENI Config Label for EKS Cluster {0}".format(self.cluster_name))
        command = constants.COMMAND_SET_ENI_CONFIG_LABEL.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)
        LOG.info("Updated ENI Config Label")

    def _create_eni_config(self):
        """
        Create ENI Config Mainfest Files
        """
        LOG.info("Creating ENI Config for POD Subnets in EKS Cluster {0}".format(self.cluster_name))

        # Read POD ENIConfig Template
        with open(os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_POD_ENI_CONFIG), 'r') as file:
            pod_eniconfig_template = file.read()

        # Get POD Data from Stack Output
        pod_security_group = self.outputs[constants.POD_SECURITY_GROUP]
        pod_subnet_ids = self.outputs[constants.POD_SUBNET_IDS]
        pod_subnet_azs = self.outputs[constants.POD_SUBNET_AZS]

        # Convert CSV into List
        pod_subnet_ids = pod_subnet_ids.split(',')
        pod_subnet_azs = pod_subnet_azs.split(',')

        # Zip the data
        pod_data = zip(pod_subnet_ids, pod_subnet_azs)

        # Iterate on each data and create a template file at tmp location
        pod_enicofig_files = []
        for subnet, avail_zone in pod_data:
            LOG.info("Generating POD ENI Config File for POD Subnet {0} in AZ {1}".format(subnet, avail_zone))
            temp = pod_eniconfig_template
            temp = temp.replace('NAME', avail_zone)
            temp = temp.replace('SECURITY_GROUP_ID', pod_security_group)
            temp = temp.replace('SUBNET_ID', subnet)
            temp_path = os.path.join("/tmp", 'pod-' + avail_zone + ".yaml")
            pod_enicofig_files.append(temp_path)

            with open(temp_path, 'w') as file:
                file.write(temp)

        # Apply POD ENI Config Files
        for template in pod_enicofig_files:
            LOG.info("Applying POD ENI Config via template {0}".format(template))
            command = constants.COMMAND_KUBECTL_APPLY.format(template, constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)

        LOG.info("Created ENI Config for POD Subnets")

    def _deploy_calico(self):
        """
        Deploy Calico CRS and Operator
        """
        LOG.info("Deploying Calico in EKS Cluster {0}".format(self.cluster_name))

        LOG.info("Deploying calico-operator")
        utils.kubectl_apply(constants.TEMPLATE_CALICO_OPERATOR,self.registry_map)

        LOG.info("Deploying calico-crs")
        utils.kubectl_apply(constants.TEMPLATE_CALICO_CRS,self.registry_map)

        LOG.info("Deployed Calico CNI in cluster. Proceeding......")

    def _generate_kube_config_for_admin(self):
        """
        Generate K8S Kube Config file for Cluster Admin
        :return: True if K8S config file is created successfully
        """
        LOG.info("Generating Kube Config for Admin User...")

        cluster_name = str(self.outputs[constants.EKS_CLUSTER_NAME])
        utils.generate_kube_config_file(cluster_name=cluster_name,
                                        region=self.aws_region,
                                        config_file_path=constants.KUBECONFIG_PATH)
        return True

    def _setup_k8s_dashboard(self):
        """
        Install Metrics Server and K8S Dashboard
        """
        LOG.info("Setting up K8S dashboard on EKS Cluster {0}".format(self.cluster_name))

        # First Deploy Metrics Server
        utils.kubectl_apply(constants.TEMPLATE_METRICS_SERVER,self.registry_map)

        # Check that Metrics Server has been deployed
        command_output = utils.execute_command(constants.COMMAND_GET_METRICS_SERVER.format(constants.KUBECONFIG_PATH))
        if 'metrics-server' not in command_output:
            raise Exception("Failed to deploy Metrics Server on EKS Cluster")

        # Deploy K8S Dashboard
        if 'dashboard' not in self.config[constants.HOSTNAMES]:
            raise Exception('The hostname for the kubernetes dashboard is missing. Check config.yaml')
        dashboard_hostname = self.config[constants.HOSTNAMES]['dashboard']
        LOG.info('Kubernetes Dashboard hostname: ' + dashboard_hostname)
        substitutions = {
            "DASHBOARD_HOSTNAME":      dashboard_hostname,
            **self.registry_map
        }
        utils.kubectl_apply(constants.TEMPLATE_K8S_DASHBOARD,substitutions)


        # Create eks-admin service role
        template_file = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_EKS_ADMIN_SERVICE_ACCOUNT)
        command = constants.COMMAND_KUBECTL_APPLY.format(template_file, constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        LOG.info("EKS Cluster Dashboard Setup Complete")

    def _delete_storage_class(self, storage_class_name):
        # First check if default gp2 storage class exists and delete it
        try:
            command = constants.COMMAND_DELETE_STORAGECLASS.format(storage_class_name,
                                                                   constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            LOG.info("{0} Storage Class Deleted".format(storage_class_name))
        except Exception as exception:
            if "notfound" in str(exception).lower():
                LOG.info("{0} Storage Class not found".format(storage_class_name))
            else:
                raise exception

    def _create_gp2_storage_class(self):
        """
        Create default GP2 Storage Class
        """
        LOG.info("Creating GP2 Storage class for AWS EBS in EKS Cluster {0}".format(self.cluster_name))

        # Read Template
        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_GP2_STORAGE_CLASS)
        with open(template_path, 'r') as file:
            content = file.read()

        kms_key_arn = self.outputs[constants.EBS_KMS_KEY_ARN]
        content = content.replace("KMS_KEY_ARN", kms_key_arn)

        # Store template at temporary location
        temp_path = os.path.join("/tmp", constants.TEMPLATE_GP2_STORAGE_CLASS)
        with open(temp_path, 'w') as file:
            file.write(content)

        # Apply the template
        command = constants.COMMAND_KUBECTL_APPLY.format(temp_path, constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        LOG.info("Created GP2 Storage class for AWS EBS")

    def _update_k8s_config_map(self):
        """
        Update K8S Config Map to allow API User Role access to K8S Cluster
        :return:
        """
        LOG.info("Updating aws_auth Config Map in EKS Cluster {0}".format(self.cluster_name))
        aws_account_id = self.outputs[constants.AWS_ACCOUNT_ID]
        sso_consumer_admin = self.get_sso_admin_role_name()
        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_AWS_AUTH_CM)

        # Read current template
        with open(template_path, 'r') as file:
            content = file.read()

        if content is None:
            raise Exception("Failed to read AWS Auth CM Template file")

        # Replace Admin Role ARN
        content = content.replace('AWS_ACCOUNT_ID', aws_account_id)
        content = content.replace('SSO-CONSUMER-ADMIN', sso_consumer_admin)

        # Write Modified Template to temp location
        modified_template_path = os.path.join("/tmp", constants.TEMPLATE_AWS_AUTH_CM)
        with open(modified_template_path, 'w') as file:
            file.write(content)

        # Execute kubectl command
        command = constants.COMMAND_KUBECTL_APPLY.format(modified_template_path, constants.KUBECONFIG_PATH)
        LOG.info("Executing command - {0}".format(command))
        utils.execute_command(command=command)

        return True

    def _apply_eks_tags_to_subnets(self):
        """
        Apply EKS specific tags to Private Subnets in VPC
        """

        LOG.info("Appling EKS Tags to Private Subnet IDs in VPC...")
        self.aws_ec2client.apply_eks_tags_to_subnet(subnet_id=self.control_plane_subnet_01_id)
        self.aws_ec2client.apply_eks_tags_to_subnet(subnet_id=self.control_plane_subnet_02_id)
        LOG.info("Applied EKS Tags to Private Subnet IDs in VPC...")

    def _create_armdocker_secret(self, namespace):
        """
        Create Secret for Armdocker or pulling images
        :param namespace: Name of namespace
        """
        command = constants.COMMAND_DELETE_ARMDOCKER_REGISTRY_SECRET.format(constants.ARMDOCKER_SECRET_NAME,
                                                                            namespace,
                                                                            constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        command = constants.COMMAND_CREATE_ARMDOCKER_REGISTRY_SECRET.format(constants.ARMDOCKER_SECRET_NAME,
                                                                            constants.ARMDOCKER_REGISTRY_URL,
                                                                            self.__armdocker_user,
                                                                            self.__armdocker_pass,
                                                                            namespace,
                                                                            constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

    def _update_endpoint_security_group(self):
        """
        Add Secondary VPC CIDR to AWS Endpoint Security Group to allow traffic from PODs to AWS Services over Private
        Links
        """

        # Get Base VPC Output
        endpoint_security_group_id = str(self.cfout[constants.BASE_VPC_STACK_NAME][constants.ENDPOINT_SECURITY_GROUP_ID])
        LOG.info("Adding Secondary VPC CIDR {0} to Endpoint Security Group {1}".format(self.secondary_vpc_cidr,
                                                                                       endpoint_security_group_id))

        self.aws_ec2client.add_ingress_rule(security_group_id=endpoint_security_group_id,
                                            from_port=-1,
                                            to_port=-1,
                                            ip_protocol="-1",
                                            cidr_ip=self.secondary_vpc_cidr)
        LOG.info("Added Secondary VPC CIDR to Endpoint Security Group")

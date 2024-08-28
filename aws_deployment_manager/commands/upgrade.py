"""
This module implements Upgrade command
"""

import logging
import re
import time

from packaging.version import Version
from aws_deployment_manager import utils
from aws_deployment_manager import constants
from aws_deployment_manager.commands.base import Base

LOG = logging.getLogger(__name__)
IMAGE_VERSION_PATTERN = r"\d+\.\d+\.\d+"


class UpgradeManager(Base):
    """ Main Class for Upgrade Command """

    def __init__(self):
        Base.__init__(self)
        self.upload_templates()
        self.__existing_node_groups = None
        self.__existing_nodes = None
        self.__new_node_group = ""

    def upgrade(self, upgrade_kube_downscaler):
        """
        Upgrade IDUN AWS Infrastructure
        """
        LOG.info("Upgrading IDUN AWS for {0}".format(self.environment_name))

        # Check if IDUN Stack Exists
        exist = self.aws_cfclient.stack_exists(stack_name=self.infra_master_stack_name)

        if not exist:
            raise Exception("IDUN Deployment {0} does not exist in region {1}".
                            format(self.infra_master_stack_name, self.aws_region))

        # Check if all PODs are healthy
        all_pods_healthy, unhealthy_pods = utils.get_unhealthy_pods(kubeconfig_path=constants.KUBECONFIG_PATH)

        if not all_pods_healthy:
            LOG.error("There are unhealthy PODs in deployment")
            for namespace, name in unhealthy_pods:
                LOG.error("POD {0} in namespace {1} is unhealthy".format(name, namespace))

            raise Exception("There are unhealthy PODs in deployment")

        # Collect data from current cluster
        self._gather_current_cluster_data()

        # Disable Cluster AutoScaler
        self.disable_cluster_auto_scaler()

        # Invoke Cloudformation Stack Update for IDUN_Infra_Master
        self.create_or_update_idun_stack()

        if not self.is_ecn_connected:
            # Invoke Cloudformation Stack Update for IDUN_Infra_Additional
            self.create_or_update_idun_additional_stack()

        # Invoke Cloudformation Stack Update for Stack Create for ALB Controller
        self.outputs = self.get_idun_stack_outputs()  # get the new values after stack update
        self.create_or_update_alb_controller_stack()

        # Update the AWS ALB Controller
        self._update_aws_lb_controller()

        if Version(self.k8sversion) > Version('1.22'):
            # CUpdate IDUN CSI Controller Stack
            self.create_or_update_csi_controller_stack()
            # Deploy EBS CSI Controller
            self.deploy_ebs_csi_controller()

        # Update Add Ons
        self._update_addons()

        # Update the kube-downscaler
        if upgrade_kube_downscaler:
            LOG.info("Upgrading the kube-downscaler")
            self.install_or_upgrade_kube_downscaler()
        else:
            LOG.info("Skipping the upgrade of kube-downscaler")
            LOG.info("Use the appropriate flag to enable the upgrade of kube-downscaler")

        # Update Node Groups
        if self._is_upgrade_needed():
            self._create_secret()
            self._update_node_groups()
        else:
            LOG.info("Upgrade of NodeGroups not needed. Skipped it.")
            self.enable_cluster_auto_scaler()

        LOG.info("SUCCESS - Upgraded IDUN AWS Infrastructure")

    def _is_upgrade_needed(self):
        """
        Checks if EKS Upgrade is needed
        # EKS Cluster Upgrade is possible in 2 scenarios
        # 1. Version of K8S in config file is higher than current EKS K8S Verison
        # 2. Node Type in config file is different than current node type in EKS Node Group
        # 3. Check if the node version has changed
        :return: True if upgrade is needed
        """

        # Get stack parameters
        stack_details = self.aws_cfclient.get_stack_details(stack_name=self.infra_master_stack_name)
        stack_parameters = utils.get_stack_parameters(stack_details=stack_details)

        # Check if K8S version has changed
        current_k8s_version = Version(stack_parameters[constants.K8S_VERSION])
        LOG.info("Current version of K8S = {0}".format(current_k8s_version))
        target_k8s_version = Version(self.k8sversion)
        LOG.info("Target version of K8S = {0}".format(target_k8s_version))

        if current_k8s_version != target_k8s_version:
            LOG.info("Change in K8S version. Check if target version is higher than current version")
            if target_k8s_version > current_k8s_version:
                LOG.info("Target version {0} is higher than current version {1}. Proceed with upgrade".
                         format(target_k8s_version, current_k8s_version))
                return True

            raise Exception("Target K8S Version {0} is lower than current version {1}.".
                                format(target_k8s_version, current_k8s_version))

        # Check if the node version has changed
        outputs = utils.get_stack_outputs(stack_details=stack_details)
        cluster_name = outputs[constants.EKS_CLUSTER_NAME]
        existing_nodegroups = self.aws_eksclient.list_nodegroups(cluster_name)
        if len(existing_nodegroups) > 1:
            raise Exception("The number of nodegroups is supposed to be 1. Found {}."
                            .format(existing_nodegroups))
        nodegroup_name = existing_nodegroups[0]
        nodegroup = self.aws_eksclient.describe_nodegroup(cluster_name, nodegroup_name)
        # Check if node type has changed
        # Getting current node type via eks client request from cluster
        nodegroup_current_instance_type = str(nodegroup['nodegroup']['instanceTypes'][0])
        LOG.info("Current Node Type = {0}".format(nodegroup_current_instance_type))
        target_node_type = self.instance_type
        LOG.info("Target Node Type = {0}".format(target_node_type))

        if nodegroup_current_instance_type != target_node_type:
            LOG.info("Node Instance type has changed. Proceeding with upgrade")
            return True
        nodegroup_version = Version(nodegroup['nodegroup']['version'])
        if nodegroup_version != target_k8s_version:
            LOG.info("Nodegroup version {} is different from target version {}".format(
                     nodegroup_version, target_k8s_version))
            if target_k8s_version > nodegroup_version:
                LOG.info("Target version {0} is higher than current nodegroup version {1}. Proceed with upgrade".
                         format(target_k8s_version, nodegroup_version))
                return True

            raise Exception("Target K8S Version {0} is lower than current nodegroup version {1}.".
                                format(target_k8s_version, current_k8s_version))

        LOG.info("There is no change in K8S version of Node Instance Type. No need for upgrade..")
        return False

    def _gather_current_cluster_data(self):
        """ Store Cluster Data before Upgrade """
        # Get IDUN Stack Output
        self.outputs = self.get_idun_stack_outputs()
        self.cluster_name = str(self.outputs[constants.EKS_CLUSTER_NAME])

        # Get Current Node Groups
        self.__existing_node_groups = self.aws_eksclient.list_nodegroups(cluster_name=self.cluster_name)

        # Get Current Nodes
        self.__existing_nodes = utils.get_nodes_in_cluster()

    def _create_secret(self):
        # Store these in secret for rollback or cleanup
        command = constants.COMMAND_DELETE_NODE_GROUPS_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                                     constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        node_groups_str = ','.join(self.__existing_node_groups)
        node_list_str = ','.join(self.__existing_nodes)
        command = constants.COMMAND_CREATE_NODE_GROUPS_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                                     node_groups_str,
                                                                     node_list_str,
                                                                     constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

    def _update_aws_lb_controller(self):
        """
        Upgrade AWS LB controller using Helm.
        """

        command=constants.COMMAND_INSTALL_TGB_CRD.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        self.install_or_upgrade_aws_lb_controller()

    def _update_addons(self):
        """ Update Add Ons """
        ## The following line seems not used anywhere in this function. Can be deleted
        # eks_versions_template = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_EKS_VERSIONS)
        # eks_versions = utils.load_config(config_path=eks_versions_template)

        # Update Kube Proxy Add On
        command = constants.COMMAND_GET_KUBE_PROXY_IMAGE + " --kubeconfig " + constants.KUBECONFIG_PATH
        kube_proxy_image, changed = _get_addon_image(name=constants.KUBE_PROXY,
                                                        command=command,
                                                        target_version=self.kube_proxy_version)
        if changed:
            LOG.info("Updating Kube Proxy...")
            command = constants.COMMAND_SET_KUBE_PROXY_IMAGE.format(kube_proxy_image, constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            LOG.info("Updated Kube Proxy")
        else:
            LOG.info("No change in image version of Kube proxy")

        # Update Core DNS Add On
        command = constants.COMMAND_GET_CORD_DNS_IMAGE + " --kubeconfig " + constants.KUBECONFIG_PATH
        core_dns_image, changed = _get_addon_image(name=constants.CORE_DNS,
                                                      command=command,
                                                      target_version=self.core_dns_version)
        if changed:
            LOG.info("Updating Core DNS...")
            command = constants.COMMAND_SET_CORE_DNS_IMAGE.format(core_dns_image, constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            LOG.info("Updated Core DNS")
        else:
            LOG.info("No change in image version of Core DNS")

        # Update Cluster Auto Scaler
        command = constants.COMMAND_GET_AUTO_SCALER_IMAGE + " --kubeconfig " + constants.KUBECONFIG_PATH
        auto_scaler_image, changed = _get_addon_image(name=constants.AUTO_SCALER,
                                                         command=command,
                                                         target_version=self.auto_scaler_version)
        if changed:
            LOG.info("Updating Cluster Auto Scaler...")
            command = constants.COMMAND_SET_AUTO_SCALER_IMAGE.format(auto_scaler_image, constants.KUBECONFIG_PATH)
            utils.execute_command(command=command)
            LOG.info("Updated Auto Scaler")
        else:
            LOG.info("No change in image version for Cluster Auto Scaler")

        # Update CNI Plugin Version
        self.update_cni_plugin()

    def _update_node_groups(self):
        """ Update Node Groups to new K8S version """
        LOG.info("Updating Node Groups for {0}".format(self.environment_name))

        LOG.info("Below nodes will be removed...")
        LOG.info(self.__existing_nodes)

        # Create a new Node Group with latest K8S version
        LOG.info("Creating New Node Group...")
        nodegroup = self.aws_eksclient.list_nodegroups(cluster_name=self.cluster_name)
        nodegroup_name = nodegroup[0]
        nodegroup_desc = self.aws_eksclient.describe_nodegroup(cluster_name=self.cluster_name,
                                                               nodegroup_name=nodegroup_name)
        if nodegroup_desc['nodegroup']['scalingConfig']['desiredSize'] + 2 > nodegroup_desc['nodegroup']['scalingConfig']['maxSize']:
            desired_size = nodegroup_desc['nodegroup']['scalingConfig']['maxSize']
        else:
            desired_size = nodegroup_desc['nodegroup']['scalingConfig']['desiredSize'] + 2
        self.__new_node_group = self.create_node_group(desired_size=desired_size)
        LOG.info("Node Group created")

        # Cordon nodes with old version
        for node in self.__existing_nodes:
            LOG.info("Cordon node {0}".format(node))
            utils.cordon_node(node_name=node, kubeconfig_path=constants.KUBECONFIG_PATH)
        LOG.info("All nodes cordoned")

        # Drain each node one by one
        for node in self.__existing_nodes:
            LOG.info("Draining node {0}".format(node))
            utils.drain_node(node_name=node, kubeconfig_path=constants.KUBECONFIG_PATH)
            LOG.info("Waiting 1 min before starting next drain...")
            time.sleep(60)
        LOG.info("All nodes drained")

        # Wait for all PODs to come up properly
        all_pods_healthy = utils.wait_for_all_pods_to_healthy(kubeconfig_path=constants.KUBECONFIG_PATH)

        if all_pods_healthy:
            LOG.info("All PODS up and running")
        else:
            raise Exception("Few PODs have not come up properly")


def _get_addon_image(name, command, target_version):
    """
    Get new image name for Add On
    :param name: Name of Add On
    :param command: Command to get current Image of Add On
    :param target_version: Target Version of Image
    :return: New Image URL
    """
    LOG.info("Getting image for add on {0}".format(name))
    current_image = utils.execute_command(command=command)
    LOG.info("Current Image = {0}".format(current_image))

    target_image = re.sub(IMAGE_VERSION_PATTERN, target_version, current_image)
    LOG.info("Target Image = {0}".format(target_image))

    if current_image != target_image:
        return target_image, True

    return target_image, False

"""
This module implements Cleanup command
"""
import logging
from aws_deployment_manager import utils
from aws_deployment_manager import constants
from aws_deployment_manager.commands.base import Base

LOG = logging.getLogger(__name__)


class CleanupManager(Base):
    """ Main Class for Cleanup Command """

    def __init__(self):
        Base.__init__(self)
        self.__node_groups_before_upgrade = None
        self.__nodes_before_upgrade = None

    def cleanup(self):
        """
        Cleanup IDUN AWS Infrastructure
        """
        LOG.info("Cleanup Started for {0}".format(self.environment_name))

        # Check if IDUN Stack Exists
        exist = self.aws_cfclient.stack_exists(stack_name=self.infra_master_stack_name)

        if not exist:
            raise Exception("IDUN Deployment {0} does not exist in region {1}".
                            format(self.infra_master_stack_name, self.aws_region))

        # Collect data
        self._gather_cluster_data()

        # Delete old node group
        self._delete_old_node_groups()

        # Enable Cluster Auto Scaler
        self.enable_cluster_auto_scaler()

        # Delete Node Group Secret
        command = constants.COMMAND_DELETE_NODE_GROUPS_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                                     constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        LOG.info("Cleanup successful for {0}".format(self.environment_name))

    def _gather_cluster_data(self):
        """
        Gather cluster data stored before upgrade
        """
        # Get IDUN Stack Output
        self.outputs = self.get_idun_stack_outputs()
        self.cluster_name = str(self.outputs[constants.EKS_CLUSTER_NAME])

        # Get Node Groups before upgrade
        command = constants.COMMAND_GET_NODE_GROUPS_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                                  constants.KUBECONFIG_PATH)
        node_groups_secret = utils.execute_command(command=command)
        if 'not found' in node_groups_secret.lower():
            raise Exception("Node Group data before upgrade could not be fetched")

        # Get Nodes before upgrade
        command = constants.COMMAND_GET_NODES_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                            constants.KUBECONFIG_PATH)
        nodes_secret = utils.execute_command(command=command)
        if 'not found' in nodes_secret.lower():
            raise Exception("Node Group data before upgrade could not be fetched")

        self.__node_groups_before_upgrade = node_groups_secret.split(",")
        self.__nodes_before_upgrade = nodes_secret.split(",")

        LOG.info("Node Groups before Upgrade = {0}".format(self.__node_groups_before_upgrade))
        LOG.info("Nodes before Upgrade = {0}".format(self.__nodes_before_upgrade))

    def _delete_old_node_groups(self):
        """
        Delete Old Node Groups
        """
        for group in self.__node_groups_before_upgrade:
            LOG.info("Deleting Node Group {0}".format(group))
            self.aws_eksclient.delete_nodegroup(cluster_name=self.cluster_name, nodegroup_name=group)

        LOG.info("All old node groups deleted")

"""
This module implements Rollback command
"""
import logging
import time
from aws_deployment_manager import utils
from aws_deployment_manager import constants
from aws_deployment_manager.commands.base import Base

LOG = logging.getLogger(__name__)


class RollbackManager(Base):
    """ Main Class for Rollback Command """

    def __init__(self):
        Base.__init__(self)
        self.__node_groups_before_upgrade = None
        self.__nodes_before_upgrade = None
        self.__new_node_groups = None
        self.__new_nodes = None

    def rollback(self):
        """
        Rollback IDUN AWS Infrastructure
        """
        LOG.info("Rollback Started for {0}".format(self.environment_name))

        # Check if IDUN Stack Exists
        exist = self.aws_cfclient.stack_exists(stack_name=self.infra_master_stack_name)

        if not exist:
            raise Exception("IDUN Deployment {0} does not exist in region {1}".
                            format(self.infra_master_stack_name, self.aws_region))

        # Collect data
        self._gather_cluster_data()

        # Cordon New Nodes
        self._cordon_new_nodes()

        # Uncordon old nodes
        self._uncordon_old_nodes()

        # Drain New Nodes
        self._drain_new_nodes()

        # Wait for all PODs to come up properly
        all_pods_healthy = utils.wait_for_all_pods_to_healthy(kubeconfig_path=constants.KUBECONFIG_PATH)

        if all_pods_healthy:
            LOG.info("All PODS up and running")
        else:
            raise Exception("Few PODs have not come up properly")

        # Delete new node group
        self._delete_new_node_groups()

        # Enable Cluster Auto Scaler
        self.enable_cluster_auto_scaler()

        # Delete Node Group Secret
        command = constants.COMMAND_DELETE_NODE_GROUPS_SECRET.format(constants.NODE_GROUPS_SECRET,
                                                                     constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        LOG.info("Rollback successful for {0}".format(self.environment_name))

    def _gather_cluster_data(self):
        """
        Gather cluster data needed for rollback
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

        # Get New Node Groups
        all_node_groups = self.aws_eksclient.list_nodegroups(cluster_name=self.cluster_name)
        self.__new_node_groups = []
        for group in all_node_groups:
            if group not in self.__node_groups_before_upgrade:
                self.__new_node_groups.append(group)

        # Get New Nodes
        all_nodes = utils.get_nodes_in_cluster()
        self.__new_nodes = []
        for node in all_nodes:
            if node not in self.__nodes_before_upgrade:
                self.__new_nodes.append(node)

        LOG.info("Node Groups before Upgrade = {0}".format(self.__node_groups_before_upgrade))
        LOG.info("Nodes before Upgrade = {0}".format(self.__nodes_before_upgrade))
        LOG.info("New Node Groups = {0}".format(self.__new_node_groups))
        LOG.info("New Nodes = {0}".format(self.__new_nodes))

    def _cordon_new_nodes(self):
        """
        Cordon new nodes
        """
        for node in self.__new_nodes:
            LOG.info("Cordon node {0}".format(node))
            utils.cordon_node(node_name=node, kubeconfig_path=constants.KUBECONFIG_PATH)

        LOG.info("All new nodes cordoned")

    def _uncordon_old_nodes(self):
        """ Uncordon nodes in old node groups """
        for node in self.__nodes_before_upgrade:
            LOG.info("Uncordon node {0}".format(node))
            utils.uncordon_node(node_name=node, kubeconfig_path=constants.KUBECONFIG_PATH)

        LOG.info("All nodes before upgrade uncordoned")

    def _drain_new_nodes(self):
        """ Drain New Nodes """
        for node in self.__new_nodes:
            LOG.info("Draining node {0}".format(node))
            utils.drain_node(node_name=node, kubeconfig_path=constants.KUBECONFIG_PATH)
            LOG.info("Wait 1 minute before draining next node...")
            time.sleep(60)

        LOG.info("All nodes drained...")

    def _delete_new_node_groups(self):
        """ Delete New Node Groups """
        for group in self.__new_node_groups:
            LOG.info("Deleting Node Group {0}".format(group))
            self.aws_eksclient.delete_nodegroup(cluster_name=self.cluster_name, nodegroup_name=group)

        LOG.info("All new node groups deleted")

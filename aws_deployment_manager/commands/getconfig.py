"""
This module implements Getconfig command
"""
import logging
from aws_deployment_manager import utils
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class GetconfigManager():
    """ Main Class for Getconfig command """
    def __init__(self, env_name, region):
        self.__environment_name = env_name
        self.__region = region
        self.__cluster_name = utils.get_cluster_name_from_stack(stack_name=self.__environment_name)

    def generate_k8s_config_file(self):
        """
        Generate KubeConfig file for IDUN Deployment
        :return: Path to K8S KubeConfig File
        """
        LOG.info("Generating Kube Config for Environment {0},  EKS Cluster {1}".
                 format(self.__environment_name, self.__cluster_name))

        utils.generate_kube_config_file(cluster_name=self.__cluster_name,
                                        region=self.__region,
                                        config_file_path=constants.KUBECONFIG_PATH)
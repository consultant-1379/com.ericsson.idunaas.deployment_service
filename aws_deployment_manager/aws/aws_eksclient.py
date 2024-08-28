"""
Wrapper class for AWS EKS Service
"""

import logging
import time
import boto3
from botocore.exceptions import ClientError
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsEKSClient(AwsBase):
    """
    Wrapper class for AWS EKS Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Cloudformation Client with AWS Region
        self.__eks_client = boto3.client(
            constants.EKS_SERVICE,
            config=self.get_aws_client_config()
        )

    def update_cluster_access_endpoints(self, cluster_name, enable_public_access, enable_private_access):
        """
        Update EKS Cluster Access Endpoints
        :param cluster_name: Name of EKS Cluster
        :param enable_public_access: Set True to enable Public Endpoint Access
        :param enable_private_access: Set True to enable Private Endpoint Access
        :return: None. Exception raised in case of failure
        """
        LOG.info("Update Endpoint access for cluster {0}. Public Access = {1}, Private Access = {2}".
                 format(cluster_name, enable_public_access, enable_private_access))

        response = self.__eks_client.update_cluster_config(
            name=cluster_name,
            resourcesVpcConfig={
                'endpointPublicAccess': enable_public_access,
                'endpointPrivateAccess': enable_private_access
            }
        )

        if response:
            update_id = response['update']['id']
            update_status = response['update']['status']

            # Wait for update to complete
            while update_status not in ['Failed', 'Cancelled', 'Successful']:
                LOG.info("Update ID = {0}, Status = {1}".format(update_id, update_status))
                time.sleep(30)
                update_status = self.check_update_status(cluster_name=cluster_name, update_id=update_id)

            LOG.info("Update complete. Status = {0}".format(update_status))

            if update_status == "Successful":
                return True

        raise Exception("Failed to update endpoint access for cluster {0}".format(cluster_name))

    def check_update_status(self, cluster_name, update_id):
        """
        Check update status for changes in cluster config
        :param cluster_name: Name of EKS Cluster
        :param update_id: ID of update request
        :return:
        """
        LOG.info("Checking status  of EKS Cluster {0} update with ID {1}".format(cluster_name, update_id))
        response = self.__eks_client.describe_update(
            name=cluster_name,
            updateId=update_id
        )

        if response:
            return response['update']['status']

        return "NA"

    def describe_cluster(self, cluster_name):
        """
        Returns descriptive information about an Amazon EKS cluster
        :param cluster_name: Name of EKS Cluster
        :return: Information about cluster
        """
        response = self.__eks_client.describe_cluster(
            name=cluster_name
        )

        if response:
            return response

        return None

    def create_nodegroup(self, cluster_name: str, nodegroup_name: str, min_size: int, max_size: int,
                         desired_size: int, disk_size: int, subnets: [str], instance_type: str, ami_type: str,
                         node_role: str, ec2_ssh_keypair_name: str):
        """
        Create NodeGroup in EKS Cluster
        :param cluster_name: Name of EKS Cluster
        :param nodegroup_name: Name of Node Group
        :param min_size: Minimum number of nodes in Node Group
        :param max_size: Maximum number of nodes in Node Group
        :param desired_size: Desired number of nodes in Node Group
        :param disk_size: Disk Size (GB) to be attached to each node
        :param subnets: Subnets (AZ) for node placement
        :param instance_type: Type of EC2 Instance
        :param ami_type: AMI Type
        :param node_role: IAM Role ARN for each node
        :param ec2_ssh_keypair_name: EC2 SSH Key Pair Name
        :return:
        """
        LOG.info("Creating Node Group {0} in EKS Cluster {1}".format(nodegroup_name, cluster_name))
        response = self.__eks_client.create_nodegroup(
            clusterName=cluster_name,
            nodegroupName=nodegroup_name,
            scalingConfig={
                'minSize': min_size,
                'maxSize': max_size,
                'desiredSize': desired_size
            },
            diskSize=disk_size,
            subnets=subnets,
            instanceTypes=[
                instance_type
            ],
            amiType=ami_type,
            remoteAccess={
                'ec2SshKey': ec2_ssh_keypair_name
            },
            nodeRole=node_role,
            capacityType='ON_DEMAND'
        )

        if response:
            LOG.info("Waiting for Node Group {0} in EKS Cluster {1} to be Active".format(nodegroup_name, cluster_name))
            status = response['nodegroup']['status']

            while status not in ['ACTIVE', 'CREATE_FAILED']:
                LOG.info("Node Group Status = {0}".format(status))
                time.sleep(30)
                nodegroup_info = self.describe_nodegroup(cluster_name=cluster_name,
                                                         nodegroup_name=nodegroup_name)
                if nodegroup_info:
                    status = nodegroup_info['nodegroup']['status']

            if status == 'ACTIVE':
                LOG.info("Node Group {0} in EKS Cluster {1} is Active".format(nodegroup_name, cluster_name))
                return

        raise Exception("Failed to create Node Group {0} in EKS Cluster {1}".format(nodegroup_name, cluster_name))

    def describe_nodegroup(self, cluster_name, nodegroup_name):
        """
        Get information about a node group in EKS Cluster
        :param cluster_name: Name of EKS Cluster
        :param nodegroup_name: Name of Node Group
        :return: Information about node group
        """
        LOG.info("Getting information about node group {0} in EKS Cluster {1}".format(nodegroup_name, cluster_name))
        response = self.__eks_client.describe_nodegroup(
            clusterName=cluster_name,
            nodegroupName=nodegroup_name
        )

        if response:
            return response

        return None

    def delete_nodegroup(self, cluster_name, nodegroup_name):
        """
        Deletes Node Group in EKS Cluster
        :param cluster_name: Name of EKS Cluster
        :param nodegroup_name:
        :return:
        """
        LOG.info("Deleting Node Group {0} in EKS Cluster {1}".format(nodegroup_name, cluster_name))
        response = self.__eks_client.delete_nodegroup(
            clusterName=cluster_name,
            nodegroupName=nodegroup_name
        )

        if response:
            LOG.info("Waiting for Node Group {0} in EKS Cluster {1} to be deleted".format(nodegroup_name, cluster_name))
            status = response['nodegroup']['status']

            while status not in ['DELETE_FAILED', 'DELETE_COMPLETE']:
                try:
                    LOG.info("Node Group Status = {0}".format(status))
                    time.sleep(30)
                    nodegroup_info = self.describe_nodegroup(cluster_name=cluster_name,
                                                             nodegroup_name=nodegroup_name)
                    if nodegroup_info:
                        status = nodegroup_info['nodegroup']['status']
                except ClientError as client_error:
                    # When node group is deleted, describe_nodegroup function will raise exception.
                    # This is the indication to know that node group has been deleted
                    if client_error.response:
                        message = str(client_error.response['Error']['Message']).lower()
                        if 'no node group found' in message:
                            status = 'DELETE_COMPLETE'
                        else:
                            raise Exception("Delete Node Group Failed for {0}. Error is - {1}".
                                            format(nodegroup_name, client_error)) from client_error
                    else:
                        raise Exception("Delete Node Group Failed for {0}. Error is - {1}".
                                        format(nodegroup_name, client_error)) from client_error
                except Exception as exception:
                    raise exception

            if status == 'DELETE_COMPLETE':
                LOG.info("Node Group {0} in EKS Cluster {1} is Deleted".format(nodegroup_name, cluster_name))
                return

        raise Exception("Failed to delete node group {0} in EKS Cluster {1}".format(nodegroup_name, cluster_name))

    def list_nodegroups(self, cluster_name):
        """
        List names of node groups in EKS Cluster
        :param cluster_name: Name of EKS Cluster
        :return: List of Node Group Names
        """
        LOG.info("Getting node groups in EKS Cluster {0}".format(cluster_name))
        response = self.__eks_client.list_nodegroups(
            clusterName=cluster_name
        )

        if response:
            nodegroups = response['nodegroups']
            LOG.info("Found {0} node groups in EKS Cluster {1}".format(len(nodegroups), cluster_name))
            return nodegroups

        raise Exception("Failed to list node groups in EKS Cluster {0}".format(cluster_name))

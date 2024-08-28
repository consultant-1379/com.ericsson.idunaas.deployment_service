"""
Wrapper class for AWS Auto Scaling Service
"""

import logging
import boto3
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsASGClient(AwsBase):
    """
    Wrapper class for AWS ASG Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Client with AWS Region
        self.__asg_client = boto3.client(
            constants.ASG_SERVICE,
            config=self.get_aws_client_config()
        )

    def describe_auto_scaling_group(self, group_name):
        """
        Get informatin about Auto Scaling Group
        :param group_name: Name of ASG
        :return: Information about ASG
        """
        response = self.__asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                group_name
            ]
        )

        if response:
            return response['AutoScalingGroups'][0]

        raise Exception("Failed to get details of Auto Scaling Group {0}".format(group_name))

    def update_scaling_configuration(self, group_name, min_size: int, max_size: int, desired_size: int):
        """
        Update scaling configuration for ASG
        :param group_name: ASG Name
        :param min_size: Number of min nodes
        :param max_size: Number of max nodes
        :param desired_size: Number of desired nodes
        """

        LOG.info("Updating Scaling config for ASG Group {0} to Min = {1}, Max = {2}, Desired = {3}".
                 format(group_name, min_size, max_size, desired_size))

        response = self.__asg_client.update_auto_scaling_group(
            AutoScalingGroupName=group_name,
            MinSize=min_size,
            MaxSize=max_size,
            DesiredCapacity=desired_size
        )

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']

            if response_code == constants.HTTP_OK:
                LOG.info("Scaling Configuration Applied. Nodes in cluster will be resized eventually")
                return

        raise Exception("Failed to change scaling configuration for ASG {0}".
                        format(group_name))

    def get_nodes_in_asg(self, group_name):
        """
        Get Nodes in ASG
        :param group_name: Name of ASG
        :return: List of nodes
        """
        LOG.info("Getting list of nodes in ASG {0}".format(group_name))
        group_info = self.describe_auto_scaling_group(group_name=group_name)
        nodes = []
        for instance in group_info['Instances']:
            nodes.append(instance['InstanceId'])

        LOG.info("Found {0} nodes in ASG {1}".format(len(nodes), group_name))
        return nodes

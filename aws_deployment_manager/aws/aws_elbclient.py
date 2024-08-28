"""
Wrapper class for AWS ELB Service
"""
import logging
import boto3
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsELBClient(AwsBase):
    """
    Wrapper class for AWS ELB Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Cloudformation Client with AWS Region
        self.__elb_client = boto3.client(
            constants.ELB_SERVICE,
            config=self.get_aws_client_config()
        )

    def get_elb_hosted_zone(self, elb_dns_name, account_id):
        """
        Get ELB Hosted Zone ID
        :param elb_dns_name: ELB DNS Name
        :param account_id: AWS Account ID
        :return: Hoted Zone ID for ELB
        """
        dns_name = elb_dns_name.replace('.elb.{0}.amazonaws.com'.format(self.get_aws_region()), '')
        LOG.info("Getting Hosted Zone name for ELB {0}".format(dns_name))
        elb_arn = self.get_arn_from_dns_name(elb_dns_name=dns_name, account_id=account_id)

        LOG.info("ARN for ELB is {0}".format(elb_arn))

        response = self.__elb_client.describe_load_balancers(
            LoadBalancerArns=[
                elb_arn
            ]
        )

        if 'LoadBalancers' in response:
            loadbalancers = response['LoadBalancers']
            if len(loadbalancers) > 1:
                raise Exception(
                    "Failed to get Hosted Zone for ELB {0}.".format(dns_name))

            elb = loadbalancers[0]
            hosted_zone = elb['CanonicalHostedZoneId']
            LOG.info("Hosted Zone for ELB {0} is {1}".format(dns_name, hosted_zone))
            return hosted_zone

        raise Exception("Failed to get Hosted Zone for ELB {0}. Please check if ELB exists".format(dns_name))

    def get_arn_from_dns_name(self, elb_dns_name, account_id):
        """
        Create ELB ARN from ELB DNS Name
        :param elb_dns_name: DNS Name of ELB
        :param account_id: AWS Account ID
        :return: ARN of ELB
        """
        return constants.ELB_ARN.format(self.get_aws_region(), account_id, str(elb_dns_name).replace('-', '/'))

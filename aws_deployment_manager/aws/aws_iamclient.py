"""
Wrapper class for AWS IAM Service
"""
import logging
import boto3
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsIAMClient(AwsBase):
    """
    Wrapper class for AWS IAM Service
    """

    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Cloudformation Client with AWS Region
        self.__iam_client = boto3.client(
            constants.IAM_SERVICE,
            config=self.get_aws_client_config()
        )

    def create_open_id_connect_provider(self, oid_url, thumb_print, env_name):
        """
        Create open_id_connect provider
        :param: OID URL, Thumbprint and Environment name
        :return: Identity Provider

        """
        try:
            LOG.info("Creating OpenID Connect Provider for IDUN Deployment {} ".format(env_name))
            response = self.__iam_client.create_open_id_connect_provider(
                Url=oid_url,
                ClientIDList=[
                    'sts.amazonaws.com',
                ],
                ThumbprintList=[
                    thumb_print,
                ]
            )
            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                open_id_provider = response['OpenIDConnectProviderArn']
                if response_code == constants.HTTP_OK:
                    LOG.info("Open_id_provider created for {} successfully".format(env_name))
                    return open_id_provider

                raise Exception("Failed to create Open_id_provider for {}".format(env_name))
        except self.__iam_client.exceptions.EntityAlreadyExistsException:
            LOG.info("OIDC already exist for deployment {}".format(env_name))
        return None

    def create_policy(self, policy_name, policy_string, env_name):
        """
        Create Policy
        :param: Policy Name, Policy String and Environment name
        :return: Policy ARN

        """
        try:
            LOG.info("Creating Policy for IDUN Deployment {} ".format(env_name))
            response = self.__iam_client.create_policy(
                PolicyName= policy_name,
                Path='/',
                PolicyDocument= policy_string,
                Description='autoscaler policy'
            )

            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']

                if response_code == constants.HTTP_OK:
                    LOG.info("policy {} created for {} successfully".format(policy_name, env_name))
                    return response['Policy']['Arn']

                raise Exception("Failed to create policy {}  for {}".format(policy_name, env_name))
        except self.__iam_client.exceptions.EntityAlreadyExistsException:
            LOG.info("Policy already exist for deployment {}".format(env_name))

        return None

    def create_role(self, role_name, role_string, env_name):
        """
        Create Role
        :param: Role Name, Role String and Environment name
        :return: Role ARN

        """
        try:
            LOG.info("Creating Role for IDUN Deployment {} ".format(env_name))
            response = self.__iam_client.create_role(
                RoleName= role_name,
                AssumeRolePolicyDocument= role_string,
                Description='Autoscaler Role',
                Tags=[
                  {
                    'Key': 'Environment',
                    'Value': env_name
                  },
                ]
            )

            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code == constants.HTTP_OK:
                    LOG.info("Role {} for {} created successfully".format(role_name, env_name))
                    return response['Role']['Arn']

                raise Exception("Failed to create Role {} for {}".format(role_name, env_name))
        except self.__iam_client.exceptions.EntityAlreadyExistsException:
            LOG.info("Policy already exist for deployment {}".format(env_name))

        return None

    def attach_role_policy(self, role_name, policy_arn):
        """
        Attach Policy to an existing Role
        :param: Role Name and Policy ARN
        :return:

        """
        LOG.info("Attaching Policy {} to Role {}".format(policy_arn, role_name))
        response = self.__iam_client.attach_role_policy(
            RoleName= role_name,
            PolicyArn = policy_arn,
        )

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']
            if response_code == constants.HTTP_OK:
                LOG.info("Policy {} attached to Role {}  successfully".format(policy_arn, role_name))
                return
            raise Exception("Failed to attach policy {} to Role {} ".format(policy_arn, role_name))

    #delete methods

    def delete_open_id_connect_provider(self, oid_arn, env_name):
        """
        Delete open_id_connect provider
        :param: OID Arn and Environment name
        :return:

        """
        LOG.info("Deleting OpenID Connect Provider for IDUN Deployment {} ".format(env_name))
        response = self.__iam_client.delete_open_id_connect_provider(
            OpenIDConnectProviderArn=oid_arn
        )
        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']
            if response_code == constants.HTTP_OK:
                LOG.info("Open_id_provider deleted for {} deployment successfully".format(env_name))
                return
            raise Exception("Failed to delete Open_id_provider for {} deployment".format(env_name))

    def delete_policy(self, policy_arn, env_name):
        """
        Delete Policy
        :param: Policy Arn, and Environment name
        :return:

        """
        LOG.info("Deleting Policy for IDUN Deployment {} ".format(env_name))
        response = self.__iam_client.delete_policy(
            PolicyArn= policy_arn
        )

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']

            if response_code == constants.HTTP_OK:
                LOG.info("policy {} deleted for {} successfully".format(policy_arn, env_name))
                return
            raise Exception("Failed to delete policy {}  for deployment {}".format(policy_arn, env_name))

    def delete_role(self, role_name, env_name):
        """
        Delete Role
        :param: Role Name  and Environment name
        :return:

        """
        try:
            LOG.info("Deleting Role for IDUN Deployment {} ".format(env_name))
            response = self.__iam_client.delete_role(
              RoleName = role_name
              )

            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code == constants.HTTP_OK:
                    LOG.info("Role {} for deployment {} deleted successfully".format(role_name, env_name))
                    return
            raise Exception("Failed to delete Role {} for {}".format(role_name, env_name))
        except self.__iam_client.exceptions.NoSuchEntityException:
            LOG.info("Role {} does not exist for deployment {}".format(role_name, env_name))

    def detach_role_policy(self, role_name, policy_arn):
        """
        Attach Policy to an existing Role
        :param: Role Name and Policy ARN
        :return:

        """
        try:
            LOG.info("Detaching Policy {} from Role {}".format(policy_arn, role_name))
            response = self.__iam_client.detach_role_policy(
                RoleName= role_name,
                PolicyArn = policy_arn,
            )

            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code == constants.HTTP_OK:
                    LOG.info("Policy {} detached from Role {}  successfully".format(policy_arn, role_name))
                    return

                raise Exception("Failed to detach policy {} to Role {} ".format(policy_arn, role_name))
        except self.__iam_client.exceptions.NoSuchEntityException:
            LOG.info("Role {} not found for detachment".format(role_name))

        return

    def list_open_id_connect_providers(self, env_name):
        """
        List OIDC
        :param:  Environment name
        :return:

        """
        LOG.info("Listing information about the IAM (OIDC) provider resource  for IDUN Deployment {} "
                 .format(env_name))
        response = self.__iam_client.list_open_id_connect_providers()

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']

            if response_code == constants.HTTP_OK:
                return response['OpenIDConnectProviderList']

        raise Exception("Failed to list OIDC for deployment {}".format( env_name))

    def list_policies(self, env_name):
        """
        List Policies
        :param: Environment name
        :return:

        """
        LOG.info("Listing Policies  for IDUN Deployment {} "
                 .format(env_name))
        response = self.__iam_client.list_policies()

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']

            if response_code == constants.HTTP_OK:
                return response['Policies']

        raise Exception("Failed to list Policies for deployment {}".format( env_name))

    def list_roles(self, env_name):
        """
        List Role ARN
        :param: Environment name
        :return:

        """
        LOG.info("Listing Roles  for IDUN Deployment {} "
                 .format(env_name))
        response = self.__iam_client.list_roles()

        if response and response['ResponseMetadata']:
            response_code = response['ResponseMetadata']['HTTPStatusCode']

            if response_code == constants.HTTP_OK:
                return response['Roles']

        raise Exception("Failed to list Roles for deployment {}".format( env_name))

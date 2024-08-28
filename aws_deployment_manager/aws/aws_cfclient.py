"""
Wrapper class for AWS Cloudformation Service
"""
import logging
import time
import boto3
from botocore.exceptions import ClientError
from aws_deployment_manager import errors
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsCFClient(AwsBase):
    """
    Wrapper class for AWS Cloudformation Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Cloudformation Client with AWS Region
        self.__cloudformation_client = boto3.client(
            constants.CLOUDFORMATION_SERVICE,
            config=self.get_aws_client_config()
        )

    def create_stack(self, stack_name, template_name, template_url, config_parameters):
        """
        Create a Cloudformation Stack
        :param stack_name: Name of the Stack
        :param template_name: Name of the CF Template
        :param template_url: S3 URL of CF Template
        :param config_parameters: Parameters for CF Template
        :return:
        """
        LOG.info("Creating Stack {0} from Template {1}".format(stack_name, template_name))
        LOG.info("Stack Parameters = {0}".format(config_parameters))

        # Check if stack with same name already exists
        exists = self.stack_exists(stack_name)
        if exists:
            # If stack with same name exists, raise error
            raise errors.AWSError("Stack with name {0} already exists".format(stack_name))

        # Validate CF Template
        self.__validate_template__(template_url=template_url)

        # Initiate Stack Create. CF will return with stack ID when stack creation starts
        stack_id = self.__initiate_create_stack(stack_name=stack_name, template_url=template_url,
                                                config_parameters=config_parameters)
        LOG.info("Stack ID = {0}".format(stack_id))

        # Wait for Stack creation to be either complete or failed
        LOG.info("Waiting for stack creation to finish...")
        response = self.__wait_for_stack_create(stack_name=stack_name, stack_id=stack_id)
        return response

    def update_stack(self, stack_name, template_name, template_url, config_parameters):
        """
        Updates Cloudformation Stack
        :param stack_name: Name of CF Stack
        :param template_name: Name of CF Template
        :param template_url: S3 URL of Template
        :param config_parameters: Template Parameters
        :return:
        """
        LOG.info("Updating Stack {0} from Template {1}".format(stack_name, template_name))
        LOG.info("Stack Parameters = {0}".format(config_parameters))

        # Check if stack with same name already exists
        exists = self.stack_exists(stack_name)
        if not exists:
            # If Stack does not exist, raise error
            raise errors.AWSError("Stack with name {0} does not exist".format(stack_name))

        # Validate the template
        self.__validate_template__(template_url=template_url)

        # Initiate stack update. CF will return stack id when update starts
        stack_id = self.__initiate_update_stack(stack_name=stack_name, template_url=template_url,
                                                config_parameters=config_parameters)
        LOG.info("Stack ID = {0}".format(stack_id))

        if stack_id is None:
            return None

        # Wait for stack update to be either complete or failed
        LOG.info("Waiting for stack update to finish...")
        response = self.__wait_for_stack_update(stack_name=stack_name, stack_id=stack_id)
        return response

    def delete_stack(self, stack_name):
        """
        Delete Cloudformation Stack
        :param stack_name: Name of the CF Stack
        :return: None
        """
        LOG.info("Deleting Stack {0}".format(stack_name))

        # Check if stack with same name already exists
        exists = self.stack_exists(stack_name)
        if not exists:
            # If stack does not exist, nothing to delete
            LOG.info("Stack {0} does not exist. Nothing to delete".format(stack_name))
#           raise Exception("Stack {0} does not exist. Nothing to delete".format(stack_name))
            return False

        LOG.info("Initiating Stack Delete for {0}".format(stack_name))
        self.__cloudformation_client.delete_stack(
            StackName=stack_name
        )

        LOG.info("Stack Deletion Initiated successfully for {0}".format(stack_name))
        deletion_status = self.__wait_for_stack_deletion(stack_name=stack_name)
        return deletion_status

    def get_stack_details(self, stack_name):
        """
        Get Stack Details
        :param stack_name: Name of CF Stack
        :return: Stack details like Stack Outputs, Stack Parameters etc
        """
        return self.__cloudformation_client.describe_stacks(StackName=stack_name)

    def __validate_template__(self, template_url):
        """
        Internal method to validate Cloudformation Stack. If template is not valid, error will be raised
        :param template_url: S3 URL of CF Stack
        """
        LOG.info("Validating Template {0}".format(template_url))

        try:
            self.__cloudformation_client.validate_template(TemplateURL=template_url)
            LOG.info("Template Validation SUCCESS")
        except Exception as exception:
            LOG.error("Template Validation FAILED")
            raise errors.AWSError("Invalid Template {0}. Error - {1}".format(template_url, exception))

    def stack_exists(self, stack_name):
        """
        Internal method to check if Cloudformation Stack exists
        :param stack_name: Name of CF Stack
        :return: True if stack exists, False if stack does not exist
        """
        LOG.info("Checking if stack {0} exists...".format(stack_name))
        existing_stack_names = []

        request_again = True

        while request_again:
            # Get list of existing stacks
            response = self.__cloudformation_client.list_stacks(
                StackStatusFilter=[
                    'CREATE_IN_PROGRESS', 'CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS',
                    'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',
                    'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_COMPLETE',
                    'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_FAILED',
                    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE', 'REVIEW_IN_PROGRESS',
                    'IMPORT_IN_PROGRESS', 'IMPORT_COMPLETE', 'IMPORT_ROLLBACK_IN_PROGRESS', 'IMPORT_ROLLBACK_FAILED',
                    'IMPORT_ROLLBACK_COMPLETE']
                )

            # Get Stack Name from the list of stacks retrieved and store in local array
            for stack in response['StackSummaries']:
                existing_stack_names.append(stack['StackName'])

            # Check if all stacks have been retrieved
            request_again = bool('NextToken' in response)

        LOG.info("Total Stacks Count = {0}".format(len(existing_stack_names)))

        # Check if stack exists
        if stack_name in existing_stack_names:
            LOG.info("Stack {0} exists".format(stack_name))
            return True

        LOG.info("Stack {0} does not exists".format(stack_name))
        return False

    def __initiate_create_stack(self, stack_name, template_url, config_parameters):
        """
        Internal method to initiate Stack Creation
        :param stack_name: Name of CF Stack
        :param template_url: S3 URL of CF Stack
        :param config_parameters: Stack Parameters
        :return: Stack ID
        """
        template_parameters = []

        # Prepare Template Parameters
        for param in config_parameters:
            temp = {'ParameterKey': param, 'ParameterValue': config_parameters[param]}
            template_parameters.append(temp)

        capabilities = ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']

        LOG.info("Initiating Stack Create for {0}".format(stack_name))
        response = self.__cloudformation_client.create_stack(
            StackName=stack_name,
            TemplateURL=template_url,
            Parameters=template_parameters,
            DisableRollback=True,
            TimeoutInMinutes=120,
            Capabilities=capabilities
        )

        if response:
            LOG.info("SUCCESS - Stack creation successfully initialized for {0}".format(stack_name))
            return response['StackId']

        raise Exception("FAILED to create stack {0} using template {1}".format(stack_name, template_url))

    def __initiate_update_stack(self, stack_name, template_url, config_parameters):
        """
        Internal method to initiate stack update
        :param stack_name: Name of CF Stack
        :param template_url: S3 URL of CF Stack
        :param config_parameters: Stack Parameters
        :return: Stack ID
        """
        template_parameters = []

        # Prepare Template Parameters
        for param in config_parameters:
            temp = {'ParameterKey': param, 'ParameterValue': config_parameters[param]}
            template_parameters.append(temp)

        capabilities = ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']

        LOG.info("Initiating Stack Update for {0}".format(stack_name))
        try:
            response = self.__cloudformation_client.update_stack(
                StackName=stack_name,
                TemplateURL=template_url,
                Parameters=template_parameters,
                Capabilities=capabilities
            )

            if response:
                LOG.info("SUCCESS - Stack update successfully initialized for {0}".format(stack_name))
                return response['StackId']

            raise Exception("FAILED to update stack {0} using template {1}".format(stack_name, template_url))
        except Exception as exception:
            message = str(exception).lower()

            if "no updates" in message:
                LOG.info("No changes to be done. Proceed further")
                return None
            raise exception

    def __wait_for_stack_create(self, stack_name, stack_id):
        """
        Internal method to wait for stack create action to finish
        :param stack_name: Name of CF Stack
        :param stack_id: Stack ID
        :return: Stack Response. If stack creation fails, error will be raised
        """
        LOG.info("Waiting for stack {0} to be created".format(stack_name))
        stack_status = None

        response = None
        # Wait till stack status is complete or failed. Check every 30 seconds
        while stack_status not in ('CREATE_COMPLETE', 'CREATE_FAILED'):
            time.sleep(10)
            response = self.__cloudformation_client.describe_stacks(
                StackName=stack_id
            )

            stack_status = response['Stacks'][0]['StackStatus']
            LOG.info("Stack Status = {0}".format(stack_status))

        if stack_status == 'CREATE_COMPLETE':
            LOG.info("CREATE COMPLETE - Stack {0}".format(stack_name))
            return response

        LOG.error("CREATE FAILED - Stack {0}".format(stack_name))
        raise Exception("Stack Creation Failed for {0}".format(stack_name))

    def __wait_for_stack_update(self, stack_name, stack_id):
        """
        Internal method to wait for stack update action to finish
        :param stack_name: Name of CF Stack
        :param stack_id: Stack ID
        :return: Stack Response. If stack update fails, error will be raised
        """
        LOG.info("Waiting for stack {0} to be updated".format(stack_name))
        stack_status = None

        response = None
        # Check every 30 sec if stack update is either complete or failed
        while stack_status not in ('UPDATE_COMPLETE', 'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE'):
            time.sleep(30)
            response = self.__cloudformation_client.describe_stacks(
                StackName=stack_id
            )

            stack_status = response['Stacks'][0]['StackStatus']
            LOG.info("Stack Status = {0}".format(stack_status))

        if stack_status == 'UPDATE_COMPLETE':
            LOG.info("UPDATE COMPLETE - Stack {0}".format(stack_name))
            return response

        LOG.error("UPDATE FAILED - Stack {0}".format(stack_name))
        raise Exception("Stack Updated Failed for {0}".format(stack_name))

    def __wait_for_stack_deletion(self, stack_name):
        """
        Internal method to wait for stack delete action to complete
        :param stack_name: Name of CF Stack
        :return:
        """
        LOG.info("Waiting for stack {0} to be deleted".format(stack_name))
        stack_status = None

        # Check every 30 sec till stack deletion is complete or failed
        while stack_status not in ('DELETE_FAILED', 'DELETE_COMPLETE'):
            try:
                time.sleep(30)
                response = self.__cloudformation_client.describe_stacks(
                    StackName=stack_name
                )

                stack_status = response['Stacks'][0]['StackStatus']
                LOG.info("Stack Status = {0}".format(stack_status))
            except ClientError as client_error:
                # When stack is deleted, describe_stacks function will raise exception. This is the indication to know
                # that stack has been deleted
                if client_error.response:
                    message = str(client_error.response['Error']['Message']).lower()
                    if 'does not exist' in message:
                        stack_status = 'DELETE_COMPLETE'
                    else:
                        raise Exception("Delete Stack Failed for {0}. Error is - {1}".
                                        format(stack_name, client_error)) from client_error
                else:
                    raise Exception("Delete Stack Failed for {0}. Error is - {1}".
                                    format(stack_name, client_error)) from client_error
            except Exception as exception:
                raise exception

        if stack_status == 'DELETE_COMPLETE':
            LOG.info("DELETE COMPLETE - Stack {0}".format(stack_name))
            return True

        LOG.error("DELETE FAILED - Stack {0}".format(stack_name))
        raise Exception("Stack Deletion Failed for {0}".format(stack_name))

    def list_stacks(self):
        return self.__cloudformation_client.list_stacks()

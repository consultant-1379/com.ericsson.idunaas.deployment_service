"""
Wrapper Class for AWS S3 Service
"""
import logging
import boto3
from aws_deployment_manager import errors
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)


class AwsS3Client(AwsBase):
    """
    Wrapper Class for AWS S3 Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)
        self.__s3client = boto3.client(constants.S3_SERVICE, config=self.get_aws_client_config())

    def create_bucket(self, bucket_name):
        """
        Creates S3 Bucket
        :param bucket_name: Bucket Name
        :return:
        """
        LOG.info("Creating bucket {0} for storing template files".format(bucket_name))

        try:
            bucket_exists = self.__bucket_exists(bucket_name=bucket_name)
            if bucket_exists:
                LOG.info("Bucket {0} already exists. Getting bucket URL...".format(bucket_name))
                # Bucket name parameter in CloudFormation for us-east-1 should be
                # 'https://' + bucket_name + ".s3.amazonaws.com/
                if self.get_aws_region() == "us-east-1":
                    bucket_url = 'https://' + bucket_name + ".s3.amazonaws.com/"
                else:
                    bucket_url = 'https://' + bucket_name + ".s3-" + self.get_aws_region() + ".amazonaws.com/"
                return bucket_url

            LOG.info("Bucket {0} does not exists. Creating now...")
            # Bucket Configuration should be None for us-east-1 (since it's default region)
            if self.get_aws_region() == "us-east-1":
                response = self.__s3client.create_bucket(
                    Bucket=bucket_name,
                )
            else:
                response = self.__s3client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.get_aws_region()
                    }
                )
            if response and response['ResponseMetadata']:
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code == constants.HTTP_OK:
                    LOG.info("Bucket {0} created successfully".format(bucket_name))
                    # Bucket name parameter in CloudFormation for us-east-1 should be
                    # 'https://' + bucket_name + ".s3.amazonaws.com/
                    if self.get_aws_region() == "us-east-1":
                        bucket_url = 'https://' + bucket_name + ".s3.amazonaws.com/"
                    else:
                        bucket_url = 'https://' + bucket_name + ".s3-" + self.get_aws_region() + ".amazonaws.com/"
                    return bucket_url

                raise Exception("Failed to create bucket {0}".format(bucket_name))

            raise Exception("Failed to create bucket {0}".format(bucket_name))
        except Exception as exception:
            raise errors.AWSError("Error in creating bucket {0}. Error is - {1}".
                                  format(bucket_name, exception))

    def delete_bucket(self, bucket_name):
        """
        Delete S3 Bucket
        :param bucket_name: Bucket Name
        """
        LOG.info("Deleting bucket {0}".format(bucket_name))

        try:
            if self.__bucket_exists(bucket_name=bucket_name):
                LOG.info("Bucket {0} exists".format(bucket_name))

                self.__delete_objects(bucket_name=bucket_name)
                LOG.info("Deleted all objects in bucket {0}".format(bucket_name))

                self.__s3client.delete_bucket(Bucket=bucket_name)
                LOG.info("SUCCESS - Deleted bucket {0}".format(bucket_name))
            else:
                LOG.info("Bucket {0} does not exist. Nothing to delete".format(bucket_name))
        except Exception as exception:
            LOG.error("Could not delete bucket {0}".format(bucket_name))
            raise errors.AWSError("Could not delete bucket {0}. Error is - {1}".
                                  format(bucket_name, exception))

    def put_object(self, filepath, key, bucket_name):
        """
        Create or Update object in S3 bucket
        :param filepath: Path of object
        :param key: Name of key to be used in S3
        :param bucket_name: Name of bucket
        :return:
        """
        try:
            self.__s3client.upload_file(Bucket=bucket_name, Filename=filepath, Key=key)
            object_url = 'https://' + bucket_name + ".s3.amazonaws.com/" + key
            return object_url
        except Exception as exception:
            LOG.error("Failed to upload file {0} to bucket {1}".format(filepath, bucket_name))
            raise errors.AWSError("Failed to upload file {0} to bucket {1}. Error is - {2}"
                                  .format(filepath, bucket_name, exception))

    def __bucket_exists(self, bucket_name):
        """
        Internal method to check if bucket exists in S3 or not
        :param bucket_name: Bucket Name
        :return: True if bucker exists else False
        """
        LOG.info("Checking if bucket {0} exists".format(bucket_name))
        existing_buckets = []
        response = self.__s3client.list_buckets()
        if response:
            for bucket in response['Buckets']:
                existing_buckets.append((bucket['Name']))

        if bucket_name in existing_buckets:
            return True
        return False

    def __delete_objects(self, bucket_name):
        """
        Internal method to delete object in S3 bucket
        :param bucket_name: Bucket Name
        """
        LOG.info("Deleting all objects in bucket {0}".format(bucket_name))
        response = self.__s3client.list_objects_v2(Bucket=bucket_name)
        if response and response['KeyCount'] > 0:
            items_to_delete = []
            for item in response['Contents']:
                temp = {}
                temp['Key'] = item['Key']
                items_to_delete.append(temp)

            LOG.info("Found {0} objects in bucket {1}".format(len(items_to_delete), bucket_name))
            delete_object = {}
            delete_object['Objects'] = items_to_delete
            delete_object['Quiet'] = True

            self.__s3client.delete_objects(Bucket=bucket_name, Delete=delete_object)

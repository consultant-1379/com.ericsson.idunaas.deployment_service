"""
Wrapper class for AWS Route53 Service
"""
import logging
import time
import random
import string
import boto3
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase
from aws_deployment_manager.aws.aws_elbclient import AwsELBClient

LOG = logging.getLogger(__name__)


class AwsR53Client(AwsBase):
    """
    Wrapper class for AWS Route53 Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        # Initialize Cloudformation Client with AWS Region
        self.__r53_client = boto3.client(
            constants.ROUTE53_SERVICE,
            config=self.get_aws_client_config()
        )

        self.__aws_elb_client = AwsELBClient(config=config)

    def hosted_zone_exists(self, hosted_zone_name):
        """
        Check if hosted zone exists
        :param hosted_zone_name: Name of hosted zone
        :return: True if hosted zone exists else False
        """
        LOG.info("Checking if hosted zone {0} exists".format(hosted_zone_name))

        # Even if we pass the DNS Name as a parameter all the Zones are given
        response = self.__r53_client.list_hosted_zones_by_name()

        if 'HostedZones' not in response or len(response['HostedZones']) == 0:
            return False

        for zone in response['HostedZones']:
            if zone['Name'].startswith(hosted_zone_name):
                LOG.info("Hosted Zone {0} exists".format(hosted_zone_name))
                return True

        LOG.info("Hosted Zone {0} DOES NOT exist".format(hosted_zone_name))
        return False

    def create_hosted_zone(self, hosted_zone_name, vpc_id):
        """
        Create Private Hosted Zone
        :param hosted_zone_name: Name of hosted zone
        :param vpc_id: VPC ID
        """
        LOG.info("Creating Hosted Zone {0} in VPC {1} Region {2}"
                 .format(hosted_zone_name, vpc_id, self.get_aws_region()))

        # First check if hosted zone exists. If yes, do nothing
        if self.hosted_zone_exists(hosted_zone_name=hosted_zone_name):
            LOG.info("Hosted Zone {0} already exists. Nothing to do".format(hosted_zone_name))
            return

        ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        response = self.__r53_client.create_hosted_zone(
            Name=hosted_zone_name,
            VPC={
                'VPCRegion': self.get_aws_region(),
                'VPCId': vpc_id
            },
            CallerReference=ref,
            HostedZoneConfig={
                'PrivateZone': True
            }
        )

        if 'ChangeInfo' in response:
            change_id = response['ChangeInfo']['Id']
            LOG.info("Hosted Zone {0} created. Change ID = {1}".format(hosted_zone_name, change_id))
            self._wait_for_change_id_sync(change_id=change_id)
        else:
            raise Exception("Error in creating hosted zone {0}. No ChangeInfo object in response".
                            format(hosted_zone_name))

    def get_hosted_zone_id(self, hosted_zone_name):
        """
        Get ID of hosted zone from Name
        :param hosted_zone_name: Name of hosted zone
        :return: ID of hosted zone
        """
        response = self.__r53_client.list_hosted_zones_by_name(
            DNSName=hosted_zone_name
        )

        if 'HostedZones' in response:
            zones = response['HostedZones']
            if len(zones) > 0:
                hosted_zone_id = response['HostedZones'][0]['Id']
                LOG.info("Hosted Zone = {0}, ID = {1}".format(hosted_zone_name, hosted_zone_id))
                return hosted_zone_id

            raise Exception("Hosted Zone {0} does not exist".format(hosted_zone_name))
        raise Exception("Failed to get response from AWS for hosted zone {0}".format(hosted_zone_name))

    def create_record(self, hosted_zone_name, record_name, elb_dns_name, account_id):
        """
        Create record of type A in hosted zone
        :param hosted_zone_name: Name of hosted zone e.g. test.ericsson.se
        :param record_name: Record name e.g. test1.test.ericsson.se
        :param elb_dns_name: DNS Name of ELB
        :param account_id: AWS Account ID
        """
        LOG.info("Creating record {0} target {1} in zone {2}".format(record_name, elb_dns_name, hosted_zone_name))

        hosted_zone_id = self.get_hosted_zone_id(hosted_zone_name=hosted_zone_name)
        elb_hosted_zone = self.__aws_elb_client.get_elb_hosted_zone(elb_dns_name=elb_dns_name,
                                                                    account_id=account_id)
        response = self.__r53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': 'A',
                            'AliasTarget': {
                                'HostedZoneId': elb_hosted_zone,
                                'DNSName': elb_dns_name,
                                'EvaluateTargetHealth': False
                            }
                        }
                    }
                ]
            }
        )

        if 'ChangeInfo' in response:
            change_id = response['ChangeInfo']['Id']
            LOG.info("Record {0} created. Waiting for change {1} to be INSYNC".format(record_name, change_id))
            self._wait_for_change_id_sync(change_id=change_id)
        else:
            raise Exception("Error in creating record {0} in hosted zone {1}. No ChangeInfo object in response".
                            format(record_name, hosted_zone_name))

    def create_records(self, hosted_zone_name, record_names, elb_dns_name, account_id):
        """
        Create multiple records of type A in private hosted zone
        :param hosted_zone_name: Name of hosted zone. e.g. test.ericsson.se
        :param record_names: Array with record names. e.g. [test1.test.ericsson.se, test2.test.ericsson.se]
        :param elb_dns_name: DNS Name of ELB
        :param account_id: AWS Account ID
        """
        hosted_zone_id = self.get_hosted_zone_id(hosted_zone_name=hosted_zone_name)
        elb_hosted_zone = self.__aws_elb_client.get_elb_hosted_zone(elb_dns_name=elb_dns_name,
                                                                    account_id=account_id)

        changes = []
        for record_name in record_names:
            LOG.info("Creating record {0} target {1} in zone {2}".format(record_name, elb_dns_name, hosted_zone_name))
            alias_target = {'HostedZoneId': elb_hosted_zone, 'DNSName': elb_dns_name, 'EvaluateTargetHealth': False}
            resource_record_set = {'Name': record_name, 'Type': 'A', 'AliasTarget': alias_target}
            change = {'Action': 'UPSERT', 'ResourceRecordSet': resource_record_set}
            changes.append(change)

        response = self.__r53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                'Changes': changes
            }
        )

        if 'ChangeInfo' in response:
            change_id = response['ChangeInfo']['Id']
            LOG.info("{0} Records created. Waiting for change {1} to be INSYNC".format(len(changes), change_id))
            self._wait_for_change_id_sync(change_id=change_id)
        else:
            raise Exception("Error in creating records in hosted zone {0}. No ChangeInfo object in response".
                            format(hosted_zone_name))

    def delete_hosted_zone(self, hosted_zone_name):
        """
        Delete hosted zone
        :param hosted_zone_name: Name of hosted zone
        """
        LOG.info("Deleting hosted zone {0}".format(hosted_zone_name))

        LOG.info("Check if hosted zone {0} exists...".format(hosted_zone_name))
        exists = self.hosted_zone_exists(hosted_zone_name=hosted_zone_name)
        if not exists:
            LOG.info("Hosted Zone {0} does not exist. Nothing to delete.".format(hosted_zone_name))
            return

        LOG.info("Checking and deleting all records in hosted zone {0}".format(hosted_zone_name))

        hosted_zone_id = self.get_hosted_zone_id(hosted_zone_name=hosted_zone_name)
        record_sets = self._get_resource_record_sets(hosted_zone_id, hosted_zone_name)
        self._delete_records_of_hosted_zone(record_sets, hosted_zone_name, hosted_zone_id)

        LOG.info("All records deleted. Deleting hosted zone now...")
        response = self.__r53_client.delete_hosted_zone(
            Id=hosted_zone_id
        )

        if 'ChangeInfo' in response:
            change_id = response['ChangeInfo']['Id']
            LOG.info("Hosted Zone {0} deleted. Waiting for change {1} to be INSYNC".
                     format(hosted_zone_name, change_id))
            self._wait_for_change_id_sync(change_id=change_id)
            return response
        raise Exception("Error in deleting hosted zone {0}. No ChangeInfo object in response".
                        format(hosted_zone_name))

    def _get_resource_record_sets(self, hosted_zone_id, hosted_zone_name):
        """
        Gets the resource record sets for a hosted zone
        :param hosted_zone_id: the ID of the hosted zone
        :return: resource_record_sets
        :rtype: list
        """
        response = self.__r53_client.list_resource_record_sets(
            HostedZoneId=hosted_zone_id
        )

        if 'ResourceRecordSets' not in response:
            raise Exception(
                "Could not delete hosted zone. Failed to get records from hosted zone {0}".
                format(hosted_zone_name))

        return response['ResourceRecordSets']

    def _delete_records_of_hosted_zone(self, record_sets, hosted_zone_name, hosted_zone_id):
        """
        Deletes the resource record sets for a hosted zone
        :param hosted_zone_name: the name of the hosted zone
        :param hosted_zone_id: the ID of the hosted zone
        :return: response
        """
        changes = []
        for record in record_sets:
            record_type = record['Type']
            if record_type not in ['NS', 'SOA']:
                change = {'Action': 'DELETE', 'ResourceRecordSet': record}
                changes.append(change)

        LOG.info(
            "Found {0} records to be deleted from zone {1}".format(len(changes), hosted_zone_name))
        if len(changes) > 0:
            response = self.__r53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': changes
                }
            )

            if 'ChangeInfo' in response:
                change_id = response['ChangeInfo']['Id']
                LOG.info(
                    "{0} Records deleted. Waiting for change {1} to be INSYNC".format(len(changes),
                                                                                      change_id))
                self._wait_for_change_id_sync(change_id=change_id)
                return response
            raise Exception("Error in deleting records in hosted zone {0}. "
                            "No ChangeInfo object in response".format(hosted_zone_name))
        else:
            LOG.info('Skipping deleting records as no records to delete were found')

    def _wait_for_change_id_sync(self, change_id):
        """
        Wait for a change to be INSYNC
        :param change_id: Change ID
        """
        change_status = None
        retry_count = 0

        while change_status not in ['INSYNC']:
            LOG.info("Checking status for change id {0}".format(change_id))
            retry_count += 1
            response = self.__r53_client.get_change(
                Id=change_id
            )

            if 'ChangeInfo' in response:
                change_status = response['ChangeInfo']['Status']
                LOG.info("Status = {0}".format(change_status))
                if change_status == 'INSYNC':
                    break

            if (change_status != 'INSYNC') and (retry_count > 10):
                raise Exception("Change ID {0} still in PENDING state".format(change_id))
            time.sleep(30)

        LOG.info("Change ID {0} is in state {1}".format(change_id, change_status))

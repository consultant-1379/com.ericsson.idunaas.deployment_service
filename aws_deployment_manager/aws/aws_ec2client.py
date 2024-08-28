"""
Wrapper Class for AWS EC2 Service
"""
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_base import AwsBase

LOG = logging.getLogger(__name__)

class AwsEC2Client(AwsBase):
    """
    Wrapper Class for AWS EC2 Service
    """
    def __init__(self, config):
        AwsBase.__init__(self, config)

        self.__client = boto3.client(constants.EC2_SERVICE, config=self.get_aws_client_config())
        self.__resource = boto3.resource(constants.EC2_SERVICE, config=self.get_aws_client_config())

    def get_primary_cidr(self, vpcid):
        """
        Get Primary CIDR for VPC
        :param: VPC ID
        :return: Primary CIDR e.g. 10.3.0.0/24
        """
        LOG.info("Getting Primary CIDR for VPC {0}...".format(vpcid))
        response = self.__client.describe_vpcs(
            VpcIds=[vpcid]
        )

        if response and ('Vpcs' in response):
            primary_cidr = response['Vpcs'][0]['CidrBlock']
            LOG.info("VPC Primary CIDR - {0}".format(primary_cidr))
            return primary_cidr

        raise Exception("Unable to get Primary CIDR for VPC {0}".format(vpcid))

    def create_securitygroup(self, group_name, vpc_id):
        """Create Security Group for the backup server"""
        LOG.info("Creating {}".format(group_name))
        response = self.__client.create_security_group(
            Description = "Security group for backup Server" ,
            GroupName = group_name ,
            VpcId = vpc_id ,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
            {
                'Key': constants.NAME,
                'Value': group_name
            },
        ]
                },
            ]
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == constants.HTTP_OK:
            LOG.info("Security group created for backup - {}".format(group_name))
            return response['GroupId']

        raise Exception("Unable to create {0}".format(group_name))

    def create_ec2(self, disk_size, user_data, image_id, instance_type, subnet_id, security_groupid, key_name,
                   snapshot_id=None):
        """
        Create ec2 Instance
        :param: Instance type, AMI type, Subnet ID, Security Group ID & ssh key pair name
        :return:
        """
        LOG.info("Creating ec2 instance")
        ebs={
                'DeleteOnTermination': False,
                'VolumeSize': disk_size,
                'VolumeType': 'standard',
                'Encrypted': True
            }
        tag_value = constants.BACKUP_SERVER
        if snapshot_id:
            ebs['SnapshotId'] = snapshot_id
            tag_value = tag_value + ' New'

        response = self.__resource.create_instances(
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sdh',
                    'Ebs': ebs,
                },
            ],
            ImageId=image_id,
            InstanceType=instance_type,
            SubnetId=subnet_id,
            KeyName=key_name,
            MaxCount=1,
            MinCount=1,
            UserData=user_data,
            SecurityGroupIds=[security_groupid],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': constants.NAME,
                            'Value': tag_value
                        },
                    ]
                },
            ],
        )
        try:
            response[0].wait_until_running()
            LOG.info("created ec2 instance successfully")
            LOG.info("The private ip is {}".format(response[0].private_ip_address))
            with open(constants.BACKUP_SERVER_IP_FILENAME, 'w+') as file_to_store_ip:
                file_to_store_ip.write(f"ip:{response[0].private_ip_address}")
        except Exception as exception:
            error_message = 'Unable to create ec2 instance'
            LOG.error(error_message, exc_info=True)
            raise Exception(error_message) from exception

        return response

    def get_subnet_availability_zone(self, subnet_id):
        """
        Get Availability Zones for Private Subnets in VPC
        :param: Subnet ID
        :return: Availability Zone Names
        """
        LOG.info("Getting Availability Zones for Private Subnet {0}".format(subnet_id))
        subnet_ids = []
        subnet_ids.append(subnet_id)

        response = self.__client.describe_subnets(
            SubnetIds=subnet_ids
        )

        subnet_azs = {}
        if response and ('Subnets' in response):
            for subnet in response['Subnets']:
                net_id = subnet['SubnetId']
                avail_zone = subnet['AvailabilityZone']
                subnet_azs[net_id] = avail_zone

            return subnet_azs[subnet_id]

        raise Exception("Unable to get Availability Zones for Subnet ID {0} in VPC".format(subnet_id))

    def apply_eks_tags_to_subnet(self, subnet_id):
        """
        Add EKS Related Tags to Private Subnets in VPC
        :param: Subnet ID
        """
        LOG.info("Applying EKS Specific lables to Private Subnet {0}...".format(subnet_id))
        subnet_ids = []
        subnet_ids.append(subnet_id)

        response = self.__client.create_tags(
            Resources=subnet_ids,
            Tags=[
                {
                    'Key': 'kubernetes.io/role/internal-elb',
                    'Value': '1'
                }
            ]
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == constants.HTTP_OK:
            LOG.info("Applied EKS Specific labels to Private Subnet {0}".format(subnet_id))
        else:
            raise Exception("Failed to apply EKS Labels to Private Subnet {0} in VPC".format(subnet_id))

    def get_route_table_ids(self, subnet_id):
        """
        Get Route Table IDs for Private Subnets in VPC
        :param: Subnet ID
        :return: Route Table ID
        """
        LOG.info("Getting Route Table IDs for Private Subnet {0}".format(subnet_id))
        response = self.__client.describe_route_tables()

        subnet_to_route_tables = {}
        for route_table in response['RouteTables']:
            route_table_id = route_table['RouteTableId']
            for assoc in route_table['Associations']:
                if 'SubnetId' in assoc:
                    net_id = assoc['SubnetId']
                    subnet_to_route_tables[net_id] = route_table_id

        return subnet_to_route_tables[subnet_id]

    def add_ingress_rule(self, security_group_id: str, from_port: int, to_port: int, ip_protocol: str, cidr_ip: str):
        """
        Add Security Group Rule to existing Security Group ID
        :param security_group_id: Name of security Group
        :param from_port: From Port
        :param to_port:To Port
        :param ip_protocol: IP Protocol
        :param cidr_ip: CIDR IP Range
        :return: Nothing. Throws Exception in case of any failure
        """
        LOG.info("Adding SG Rule (From Port - {0}, To Port - {1}, IP Protocol - {2}, CIDR IP - {3}) to SG {4}".
                 format(from_port, to_port, ip_protocol, cidr_ip, security_group_id))
        security_group = self.__resource.SecurityGroup(security_group_id)
        try:
            response = security_group.authorize_ingress(
                IpPermissions=[
                    {
                        'FromPort': from_port,
                        'IpProtocol': ip_protocol,
                        'IpRanges': [
                            {
                                'CidrIp': cidr_ip
                            },
                        ],
                        'ToPort': to_port
                    }
                ]
            )

            if response:
                if response['ResponseMetadata']['HTTPStatusCode'] == constants.HTTP_OK:
                    LOG.info("Added SG rule to SG {0}".format(security_group_id))
                    return

            raise Exception("Failed to add SG Rule to SG {0}".format(security_group_id))
        except ClientError as error:
            if 'duplicate' in error.response['Error']['Code'].lower():
                LOG.info("SG Rule already exixts in SG {0}".format(security_group_id))

    def remove_ingress_rule(self, security_group_id: str, from_port: int, to_port: int, ip_protocol: str, cidr_ip: str):
        """
        Remove Security Group Rule to existing Security Group ID
        :param security_group_id: Name of security Group
        :param from_port: From Port
        :param to_port:To Port
        :param ip_protocol: IP Protocol
        :param cidr_ip: CIDR IP Range
        :return: Nothing. Throws Exception in case of any failure
        """
        LOG.info("Removing SG Rule (From Port - {0}, To Port - {1}, IP Protocol - {2}, CIDR IP - {3}) from SG {4}".
                 format(from_port, to_port, ip_protocol, cidr_ip, security_group_id))
        security_group = self.__resource.SecurityGroup(security_group_id)
        try:
            response = security_group.revoke_ingress(
                IpPermissions=[
                    {
                        'FromPort': from_port,
                        'IpProtocol': ip_protocol,
                        'IpRanges': [
                            {
                                'CidrIp': cidr_ip
                            },
                        ],
                        'ToPort': to_port
                    }
                ]
            )

            if response:
                if response['Return']:
                    LOG.info("Removed SG rule from SG {0}".format(security_group_id))
                    return

            raise Exception("Failed to remove SG Rule from SG {0}".format(security_group_id))
        except ClientError as error:
            if 'notfound' in error.response['Error']['Code'].lower():
                LOG.info("SG Rule does not exist in SG {0}".format(security_group_id))

    def get_instance_details_from_tag(self, tag_name):
        """Get the ID of an EC2 Instance, the volume_id of the volume which will not
           be deleted on termination and the security_group_id.
           The instance is selected based on the tag 'Name' which match the parameter 'tag_name'
        """
        response = self.__client.describe_instances(Filters=[
            {
                "Name": "tag:"+constants.NAME,
                "Values": [tag_name],
            }
        ]).get("Reservations")
        for reservation in response:
            for instance in reservation["Instances"]:
                instance_id = instance.get('InstanceId')
                for volume in instance["BlockDeviceMappings"]:
                    if not volume["Ebs"]["DeleteOnTermination"]:
                        volume_id=volume["Ebs"]["VolumeId"]
                for security_group in instance['SecurityGroups']:
                    security_group_id = security_group['GroupId']
        if (volume_id is None) or (security_group_id is None) or (instance_id is None):
            raise Exception("Unable to get Volume Id or Instance Id or Security Group Id for the Instance with tag "
                            "backup Server")
        return instance_id, volume_id, security_group_id

    def create_ebs_snapshot(self, volume_id):
        """Create a Snapshot of an EBS volume"""
        current_datetime = datetime.now()
        response = self.__resource.create_snapshot(
            Description=f'Snapshot taken for {volume_id} at {current_datetime}',
            VolumeId=volume_id,
            TagSpecifications=[
                {
                    'ResourceType': 'snapshot',
                    'Tags': [
                        {
                            'Key': constants.NAME,
                            'Value': f'Snapshot-{volume_id}-backup-server'
                        },
                    ]
                },
            ],
        )
        snapshot_id = response.id
        LOG.info("Waiting for snapshot {} to be created".format(snapshot_id))

        self.__wait_until_snapshot_completed(snapshot_id)
        old_backup_volume_label = constants.OLD_VOLUME_LABEL.format(datetime.today().strftime('%Y-%m-%d'))
        self.update_tag(volume_id, constants.NAME, old_backup_volume_label)

        # OLD 1:
        # snapshot_state = None
        # # set timeout and raise exception
        # while snapshot_state != 'completed':
        #     describe_snapshot_response = self.__client.describe_snapshots(
        #         SnapshotIds=[snapshot_id]
        #     )
        #     snapshot_state = describe_snapshot_response.get('Snapshots')[0]['State']
        #     time.sleep(10)

        # OLD 2:
        #response.wait_until_completed()

        LOG.info("Snapshot created completed")

        return snapshot_id

    def update_tag(self, resource_id, tag_key, tag_value):
        """Update the tag of a taggable resource"""
        LOG.info("Updating the tag '{}' of resource {} to '{}'".format(tag_key, resource_id, tag_value))
        response = self.__client.create_tags(Resources=[resource_id], Tags=[{'Key': tag_key, 'Value': tag_value}])
        LOG.info("Updating tags completed")
        return response

    def __wait_until_snapshot_completed(self, snapshot_id):
        snapshot_waiter = self.__client.get_waiter('snapshot_completed')
        snapshot_waiter.wait(
            SnapshotIds=[snapshot_id],
            WaiterConfig={
                'Delay': 60,
                'MaxAttempts': 120
            })

    def delete_ec2(self, instance_id):
        """Delete an EC2 Instance"""
        instance = self.__resource.Instance(instance_id)
        LOG.info("Checking if instance is in running state before executing terminate")
        if instance.state['Name'] != 'running':
            raise Exception(f"The instance {instance_id} is not in Running state or the instance doesn't exist. Hence "
                            f"this cannot be terminated")

        LOG.info("Terminating the old backup server instance {}".format(instance_id))
        response = instance.terminate()
        instance.wait_until_terminated()
        return response

    def delete_volume(self, volume_id):
        """Delete an EBS Volume"""
        volume = self.__resource.Volume(volume_id)
        LOG.info("Checking if volume is in 'available' state")
        if volume.state != 'available':
            raise Exception(f"The volume {volume_id} is not in 'available' state or the volume doesn't exist. Hence "
                            f"this cannot be deleted")
        volume.delete()
        LOG.info("Volume {} deleted".format(volume_id))
        # volume_deleted_waiter = self.__client.get_waiter('volume_deleted')
        # volume_deleted_waiter.wait()

    def delete_snapshot(self, snapshot_id):
        """Delete an AWS Snapshot"""
        response = self.__client.delete_snapshot(SnapshotId=snapshot_id)
        LOG.debug(response)
        LOG.info("Snapshot {} deleted".format(snapshot_id))


"""
Setup test configuration file for pytest
"""

import os
import pytest

from _pytest.monkeypatch import MonkeyPatch

import boto3
import localstack_client.session

VALID_CONFIG_FILE_PATH = "/workdir/config.yaml"


@pytest.fixture(scope="session", autouse=True)
def setup_boto3_localstack_patch():
    """
    Mocks boto3 so that its redirected to AWS Localstack.
    """
    monkeypatch = MonkeyPatch()
    session_ls = localstack_client.session.Session()
    monkeypatch.setattr(boto3, "client", session_ls.client)
    monkeypatch.setattr(boto3, "resource", session_ls.resource)


@pytest.fixture(scope="session")
def setup_config_file():
    """
    Sets up the config.yaml file needed for tests and deletes it after all tests have finished.
    """
    ec2_client = boto3.client('ec2')
    vpcs = ec2_client.describe_vpcs()
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    subnets = ec2_client.describe_subnets()
    subnets_list = subnets['Subnets']
    route_tables = ec2_client.describe_route_tables()
    route_table_id = route_tables['RouteTables'][0]['RouteTableId']
    for subnet in subnets_list:
        ec2_client.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet['SubnetId'])
    secondary_vpc_cidr = subnets_list[0]['CidrBlock']
    write_config_file(vpc_id, subnets_list, secondary_vpc_cidr)
    yield
    os.remove(VALID_CONFIG_FILE_PATH)


def write_config_file(vpc_id, subnets_list, secondary_vpc_cidr):
    """
    Takes information about the recently created VPC and Subnets and generates a config file
    with the corresponding information.
    :param vpc_id:
    :param subnets_list:
    :param secondary_vpc_cidr:
    """
    content = f'''
EnvironmentName: idun-2
AWSRegion: eu-west-1
VPCID: {vpc_id}
ControlPlaneSubnetIds: {subnets_list[1]['SubnetId']},{subnets_list[2]['SubnetId']}
WorkerNodeSubnetIds: {subnets_list[1]['SubnetId']}
SecondaryVpcCIDR: {secondary_vpc_cidr}
DisablePublicAccess: True
NodeInstanceType: m5.2xlarge
DiskSize: 20
MinNodes: 8
MaxNodes: 10
SshKeyPairName: test-idun-keypair
PrivateDomainName: idunaas.ericsson.se
K8SVersion: '1.24'
KubeDownscaler: true
BackupInstanceType: t3.medium
BackupAmiId: ami00a40405a13c972f4
BackupDisk: 50
BackupPass: pass
Hostnames:
  so: so.eo.idunaas.ericsson.se
  pf: pf.eo.idunaas.ericsson.se
  iam: iam.eo.idunaas.ericsson.se
  uds: uds.eo.idunaas.ericsson.se
'''
    with open(VALID_CONFIG_FILE_PATH, 'w') as file:
        file.writelines(content)

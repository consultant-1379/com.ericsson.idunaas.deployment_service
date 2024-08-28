"""
This module implements Delete command
"""
import logging
import os
import tempfile
import shutil
from aws_deployment_manager import utils
from aws_deployment_manager import constants
from aws_deployment_manager.aws.aws_cfclient import AwsCFClient
from aws_deployment_manager.aws.aws_r53client import AwsR53Client
from aws_deployment_manager.aws.aws_ec2client import AwsEC2Client
from aws_deployment_manager.aws.aws_eksclient import AwsEKSClient
from aws_deployment_manager.aws.aws_iamclient import AwsIAMClient
from aws_deployment_manager.aws.aws_s3client import AwsS3Client

LOG = logging.getLogger(__name__)

class DeleteManager():
    """ Main Class for Delete command """
    def __init__(self, env_name, region):
        self.__environment_name = env_name
        self.infra_master_stack_name = env_name
        self.infra_add_stack_name = env_name + constants.IDUN_ADDITIONAL_SUFFIX_STACK_NAME
        self.alb_controller_stack_name = env_name  + constants.ALB_CONTROLLER_SUFFIX_STACK_NAME
        self.csi_controller_stack_name = env_name + constants.CSI_CONTROLLER_SUFFIX_STACK_NAME
        self.__base_vpc_stack_name = constants.BASE_VPC_STACK_NAME
        self.__region = region
        self.__cluster_name = utils.get_cluster_name_from_stack(stack_name=self.infra_master_stack_name)

        config = {constants.AWS_REGION: region}
        self.__aws_cfclient = AwsCFClient(config=config)
        self.__aws_r53client = AwsR53Client(config=config)
        self.__aws_ec2client = AwsEC2Client(config=config)
        self.__aws_eksclient = AwsEKSClient(config=config)
        self.__aws_iamclient = AwsIAMClient(config=config)
        self.__aws_s3client = AwsS3Client(config=config)

        # Create temporary directory for storing kubeconfig file
        temp_dir = tempfile.TemporaryDirectory()
        self.__temp_dir_name = temp_dir.name
        self.__config_path = os.path.join(self.__temp_dir_name, constants.KUBECONFIG_NAME)

        self.__endpoint_security_group_id = ""
        self.__secondary_vpc_cidr = ""

    def delete(self):
        """
        Delete IDUN AWS Deployment
        """
        try:
            LOG.info("Deleting IDUN AWS for {0}".format(self.__environment_name))

            # Check if IDUN Stack Exists
            exist = self.__aws_cfclient.stack_exists(stack_name=self.infra_master_stack_name)

            if not exist:
                raise Exception("IDUN Deployment {0} does not exist in region {1}".
                                format(self.infra_master_stack_name, self.__region))

            # Generate Kubeconfig file temporarily
            self._generate_kubeconfig_file()

            # Deleting Cluster Autoscaler deployment and dependent resources before other applications
            self._delete_autoscaler_resources()

            self._delete_kube_downscaler()

            # Delete all helm deployments
            self._delete_helm_deployments()

            # Delete all PVCs
            self._delete_all_pvcs()

            # Delete NGINX Controller
            self._delete_nginx_controller()

            # Delete Private Hosted Zone
            #self._delete_private_hosted_zone()

            if self.__aws_cfclient.stack_exists(self.csi_controller_stack_name):
                self._delete_cf_stack(self.csi_controller_stack_name)

            if self.__aws_cfclient.stack_exists(self.alb_controller_stack_name):
                self._delete_cf_stack(self.alb_controller_stack_name)

            if self.__aws_cfclient.stack_exists(self.infra_add_stack_name):
                self._delete_cf_stack(self.infra_add_stack_name)

            if self.__aws_cfclient.stack_exists(self.infra_master_stack_name):
                # Get Secondary VPC CIDR from Stack before deleting
                stack_details = self.__aws_cfclient.get_stack_details(self.infra_master_stack_name)
                outputs = utils.get_stack_parameters(stack_details=stack_details)
                self.__secondary_vpc_cidr = str(outputs[constants.SECONDARY_VPC_CIDR])

                # Delete Node Groups in EKS Cluster
                self._delete_node_groups(cluster_name=self.__cluster_name)

                # Delete IDUN Stack
                self._delete_cf_stack(self.infra_master_stack_name)

                # Delete SG Rule from Endpoint SG
                self._delete_security_group_from_endpoint()

            # Delete temp dir
            shutil.rmtree(self.__temp_dir_name)

            # Delete S3 Bucket used for templates
            self._delete_templates_bucket()

            LOG.info("SUCCESS - Deleted IDUN AWS Stack")
        except Exception as exception:
            raise exception

    def _delete_helm_deployments(self):
        """
        Delete all Helm Deployments
        """
        LOG.info("Deleting all helm deployments in {0}".format(self.__environment_name))

        # Get all Helm Deployments
        helm_deployments = self._get_helm_deployments()

        for deployment in helm_deployments:
            name = deployment['name']
            namespace = deployment['ns']
            self._delete_helm_deployment(name=name, namespace=namespace)

        LOG.info("Deleted all helm deployments in {0}".format(self.__environment_name))

    def _delete_all_pvcs(self):
        """
        Delete all PVCs in K8S cluster
        """
        LOG.info("Deleting all PVCs in {0}".format(self.__environment_name))

        # Get all namespaces
        namespaces = self._get_namespaces()

        # Delete PVCs in each namespace
        for namespace in namespaces:
            pvcs = self._get_pvcs_in_ns(namespace=namespace)
            if len(pvcs) > 0:
                self._delete_pvcs_in_ns(namespace=namespace)

        LOG.info("Deleted all PVCs in {0}".format(self.__environment_name))

    def _get_namespaces(self):
        """
        Get all namespaces from K8S cluster
        :return: List of namespaces
        """

        LOG.info("Getting name of namespaces in cluster {0}".format(self.__environment_name))
        command = constants.COMMAND_GET_NAMESPACES.format(self.__config_path)
        command_output = utils.execute_command(command=command)

        namespaces = []
        lines = command_output.split("\n")
        for line in lines[1:]:
            if line:
                temp = line.split()
                if temp:
                    namespaces.append(temp[0])

        LOG.info("Found {0} namespaces in K8S cluster".format(len(namespaces)))
        LOG.info(namespaces)
        return namespaces

    def _get_pvcs_in_ns(self, namespace):
        """
        Get all PVCs in a namespace from K8S cluster
        :param: Name of namespace
        :return: List of PVCs
        """

        LOG.info("Getting all PVCs in namespace {0} in cluster {1}".format(namespace, self.__environment_name))
        command = constants.COMMAND_GET_PVCS.format(namespace, self.__config_path)
        command_output = utils.execute_command(command=command)

        pvcs = []
        if 'no resources found' in command_output.lower():
            LOG.info("No PVCs in namespace {0}".format(namespace))
        else:
            lines = command_output.split("\n")
            for line in lines[1:]:
                if line:
                    temp = line.split()
                    if temp:
                        pvcs.append(temp[0])

        LOG.info("Found {0} PVCs in namespace {1} in K8S cluster".format(len(pvcs), namespace))
        return pvcs

    def _get_helm_deployments(self):
        """
        Get all deployments managed by helm
        :return: Map of helm deployments with name and ns
        """
        LOG.info("Getting Helm Deployments in {0}".format(self.__environment_name))
        command = constants.COMMAND_GET_HELM_DEPLOYMENTS.format(self.__config_path)
        command_output = utils.execute_command(command=command)

        helm_deployments = []
        lines = command_output.split("\n")
        for line in lines[1:]:
            if line:
                temp = line.split()
                if temp:
                    deployment = {'name': temp[0], 'ns': temp[1]}
                    helm_deployments.append(deployment)

        LOG.info("Found {0} deployments managed by helm".format(len(helm_deployments)))
        return helm_deployments

    def _delete_pvcs_in_ns(self, namespace):
        """
        Delete all PVCs in give namespace
        :param namespace: Name of namespace
        """
        LOG.info("Deleting all PVCs in namespace {0} in cluster {1}".format(namespace, self.__environment_name))
        command = constants.COMMAND_DELETE_PVCS.format(namespace, self.__config_path)
        utils.execute_command(command=command)
        LOG.info("Deleted all PVCs in namespace {0}".format(namespace))

    def _delete_helm_deployment(self, name, namespace):
        """
        Delete single Helm Deployment
        :param name: Name of deployment
        :param namespace: Namespace of deployment
        """
        LOG.info("Deleting Helm Deployment {0} in Namespace {1} in cluster {2}".
                 format(name, namespace, self.__environment_name))
        command = constants.COMMAND_HELM_UNINSTALL_NO_HOOKS.format(name, namespace, self.__config_path)
        utils.execute_command(command=command)
        LOG.info("Deleted Helm Deployment {0} in Namespace {1}".format(name, namespace))

    def _delete_cf_stack(self, stack_name):
        """
        Delete CloudFormation Stack
        """
        LOG.info("Deleting CloudFromation Stack {0}".format(stack_name))
        deletion_status = self.__aws_cfclient.delete_stack(stack_name=stack_name)
        LOG.info("Deleted CloudFromation Stack {0}".format(stack_name))
        return deletion_status

    def get_aws_cfclient(self):
        return self.__aws_cfclient

    def _delete_security_group_from_endpoint(self):
        """
        Delete IDUN Base VPC Security Group from Security Group Endpoint
        """
        stack_details = self.__aws_cfclient.get_stack_details(self.__base_vpc_stack_name)
        outputs = utils.get_stack_outputs(stack_details=stack_details)
        self.__endpoint_security_group_id = str(outputs[constants.ENDPOINT_SECURITY_GROUP_ID])
        self._update_endpoint_security_group()

    def _delete_nginx_controller(self):
        """
        Delete NGINX Controller
        """
        LOG.info("Removing NGINX Controller in EKS Cluster {0}".format(self.__environment_name))

        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_NGINX_CONTROLLER)
        command = constants.COMMAND_KUBECTL_DELETE.format(template_path, self.__config_path)
        try:
            utils.execute_command(command=command)
        except Exception as exception:
            LOG.info(exception)

        LOG.info("Removed NGINX Controller")

    def _delete_private_hosted_zone(self):
        """
        Deletes Private Hosted DNS Zone
        """
        stack_details = self.__aws_cfclient.get_stack_details(stack_name=self.infra_master_stack_name)
        outputs = utils.get_stack_outputs(stack_details=stack_details)
        dns_hosted_zone = outputs[constants.PRIVATE_DOMAIN_NAME]

        LOG.info("Deleting Private Hosted Zone {0}".format(dns_hosted_zone))
        self.__aws_r53client.delete_hosted_zone(hosted_zone_name=dns_hosted_zone)
        LOG.info("Deleted Private Hosted Zone {0}".format(dns_hosted_zone))

    def _generate_kubeconfig_file(self):
        """
        Generate Kubeconfig file
        :return: Path to kubeconfig file
        """
        utils.generate_kube_config_file(cluster_name=self.__cluster_name,
                                        region=self.__region,
                                        config_file_path=self.__config_path)

    def _update_endpoint_security_group(self):
        """
        Removes Secondary VPC CIDR to AWS Endpoint Security Group to allow traffic from PODs to AWS Services over
        Private Links
        """
        LOG.info("Removing Secondary VPC CIDR {0} from Endpoint Security Group {1}".
                 format(self.__secondary_vpc_cidr, self.__endpoint_security_group_id))

        self.__aws_ec2client.remove_ingress_rule(security_group_id=self.__endpoint_security_group_id,
                                                 from_port=-1,
                                                 to_port=-1,
                                                 ip_protocol="-1",
                                                 cidr_ip=self.__secondary_vpc_cidr)
        LOG.info("Removed Secondary VPC CIDR from Endpoint Security Group")

    def _delete_autoscaler_resources(self):
        """
        Delete all resources created for cluster_autoscaler in IAM and EKS cluster
        """

        LOG.info("Removing autoscaler resources for {} deployment".format(self.__environment_name))
        cluster_config = self.__aws_eksclient.describe_cluster(cluster_name=self.__cluster_name)
        cluster_oid_url = cluster_config['cluster']['identity']['oidc']['issuer']

        oid_arn = self._get_oid_arn(cluster_oid_url=cluster_oid_url, env_name=self.__environment_name)

        if oid_arn:
            self.__aws_iamclient.delete_open_id_connect_provider(oid_arn=oid_arn, env_name=self.__environment_name)
        else:
            LOG.info("No Identity Providers found for cluster {}".format(self.__cluster_name))

        role_name = constants.AUTOSCALER_IAM_ROLE.format(self.__environment_name)
        policy_name = constants.AUTOSCALER_IAM_POLICY.format(self.__environment_name)
        policy_arn = self._get_policy_arn(autoscaler_iam_policy_name=policy_name, env_name=self.__environment_name)

        if policy_arn:
            self.__aws_iamclient.detach_role_policy(role_name=role_name, policy_arn=policy_arn)
            self.__aws_iamclient.delete_policy(policy_arn=policy_arn, env_name=self.__environment_name)
        else:
            LOG.info("AutoscalerPolicy does not exist for cluster {}".format(self.__cluster_name))
        self.__aws_iamclient.delete_role(role_name=role_name, env_name=self.__environment_name)

        LOG.info("Deleting cluster_autoscaler deployment.apps in  kube-system namespace in cluster ")
        command = constants.COMMAND_GET_AUTOSCALER.format(self.__config_path)
        command_output = utils.execute_command(command=command)

        if 'no resources found' in command_output.lower():
            LOG.info("cluster_autoscaler deployment.apps does not exist in namespace kube-system")
        else:
            command = constants.COMMAND_DELETE_AUTOSCALER.format(self.__config_path)
            utils.execute_command(command=command)
            LOG.info("Deleted cluster_autoscaler deployment.apps in namespace kube-system")

        LOG.info("Removed Cluster Autoscaler resources for {} deployment".format(self.__environment_name))

    def _get_policy_arn(self, autoscaler_iam_policy_name, env_name):
        policy_list = self.__aws_iamclient.list_policies(env_name)
        policy_output = [x['Arn'] for x in policy_list if autoscaler_iam_policy_name == x['PolicyName']]
        policy_arn = ' '.join(map(str, policy_output))
        return policy_arn

    def _get_oid_arn(self, cluster_oid_url, env_name):
        oid_cluster = cluster_oid_url.split('/')[4]
        oid_arn_list = self.__aws_iamclient.list_open_id_connect_providers(env_name)
        oid_arn_output = [x['Arn'] for x in oid_arn_list if oid_cluster in x['Arn']]
        open_id_arn = ' '.join(map(str, oid_arn_output))
        return open_id_arn

    def _delete_node_groups(self, cluster_name):
        """
        Delete all node groups in EKS Cluster
        :param cluster_name: Name of EKS Cluster
        """
        LOG.info("Deleting all node groups in EKS Cluster {0}".format(cluster_name))

        # Get list of node groups
        nodegroups = self.__aws_eksclient.list_nodegroups(cluster_name=cluster_name)

        if len(nodegroups) > 0:
            for group in nodegroups:
                self.__aws_eksclient.delete_nodegroup(cluster_name=cluster_name,
                                                      nodegroup_name=group)

        LOG.info("Deleted all node groups in EKS Cluster {0}".format(cluster_name))

    def _delete_templates_bucket(self):
        """ Deletes S3 bucket where CF templates are stored"""
        bucket_name = str(self.__environment_name).lower() + constants.BUCKET_POSTFIX
        self.__aws_s3client.delete_bucket(bucket_name=bucket_name)

    def _delete_kube_downscaler(self):
        LOG.info("Deleting kube_downscaler deployment.apps in  kube-system namespace in cluster ")

        command = constants.COMMAND_GET_DOWNSCALER.format(self.__config_path)
        command_output = utils.execute_command(command=command)

        if 'no resources found' in command_output.lower():
            LOG.info("kube_downscaler deployment.apps does not exist in namespace kube-system")
        else:
            command = constants.COMMAND_DELETE_DOWNSCALER.format(self.__config_path)
            utils.execute_command(command=command)
            LOG.info("Deleted kube_downscaler deployment.apps in namespace kube-system")

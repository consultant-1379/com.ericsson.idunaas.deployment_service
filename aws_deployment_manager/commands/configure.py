"""
This module implements Configure command
"""
import logging
import os
import json
import time
import re
import tempfile
import requests
from aws_deployment_manager.commands.base import Base
from aws_deployment_manager import utils
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class ConfigureManager(Base):
    """ Main Class for Configure command """
    def __init__(self, namespace):
        Base.__init__(self)
        self.eiap_namespace = namespace
        self.cluster_name = ""
        self.outputs = self.get_idun_stack_outputs()

        # CloudFormation stack Output
        self.cfout[constants.BASE_VPC_STACK_NAME] = self.get_cf_stack_outputs(constants.BASE_VPC_STACK_NAME)
        self.cfout[self.infra_master_stack_name] = self.get_cf_stack_outputs(self.infra_master_stack_name)
        if not self.is_ecn_connected:
            self.cfout[constants.BASE_ADDITIONAL_STACK_NAME] = self.get_cf_stack_outputs(constants.BASE_ADDITIONAL_STACK_NAME)
            self.cfout[self.infra_add_stack_name] = self.get_cf_stack_outputs(self.infra_add_stack_name)
        self.cfout[self.csi_controller_stack_name] = self.get_cf_stack_outputs(self.csi_controller_stack_name)
        LOG.debug("self.cfout = {}".format(self.cfout))

        self.role_arn = ""
        self.autoscaler_iam_role = constants.AUTOSCALER_IAM_ROLE.format(self.environment_name)
        self.load_stage_states(stage_log_path=constants.INSTALL_STAGE_LOG_PATH)

    def configure(self):
        """
        IDUN Configuration Tasks
        """
        LOG.info("Executing IDUN Configuration Tasks...")
        if constants.EKS_CLUSTER_NAME in self.outputs:
            self.cluster_name = str(self.outputs[constants.EKS_CLUSTER_NAME])

            # Deploy NGINX Controller with front end private network load balancer
            self.execute_stage(func=self._deploy_nginx_controller,
                               stage=constants.CONFIGURE_STAGE_DEPLOY_NGINX_CONTROLLER)

            # Create AWS LB controller Service Account
            self.execute_stage(func=self._create_service_account_alb,
                               stage=constants.CONFIGURE_STAGE_CREATE_SA_ALB_CONTROLLER)

            # Install AWS LB controller
            self.execute_stage(func=self.install_or_upgrade_aws_lb_controller,
                               stage=constants.CONFIGURE_STAGE_INSTALL_ALB_CONTROLLER)

            # Created Private Hosted Zone and update records
            self.execute_stage(func=self._create_hosted_zone,
                               stage=constants.CONFIGURE_STAGE_CREATED_HOSTED_ZONE)

            # Deploy autoscaler with webidentity service account role
            self.execute_stage(func=self._deploy_cluster_autoscaler,
                               stage=constants.CONFIGURE_STAGE_DEPLOY_AUTO_SCALER)

            # Deploy kube-downscaler
            self.execute_stage(func=self.install_or_upgrade_kube_downscaler,
                               stage=constants.CONFIGURE_STAGE_DEPLOY_KUBE_DOWNSCALER)

            # Deploy Prometheus
            self.execute_stage(func=self._deploy_prometheus,
                               stage=constants.CONFIGURE_STAGE_DEPLOY_PROMETHEUS)

            LOG.info("IDUN Configuration done")
        else:
            raise Exception("Failed to execute IDUN Configuration steps. "
                            "Not able to get Cluster Name from Stack Output. "
                            "Stack Name is {0}".format(self.infra_master_stack_name))

    def _deploy_nginx_controller(self):
        """
        Deploy NGINX Controller
        """
        LOG.info("Deploying NGINX Controller in EKS Cluster {0}".format(self.cluster_name))
        utils.kubectl_apply(constants.TEMPLATE_NGINX_CONTROLLER,self.registry_map)

        # Wait for 3 mins for Ingress Controller to setup
        LOG.info("Waiting for NGINX Controller to come up properly...")
        time.sleep(180)

        LOG.info("Deployed NGINX Controller")

    def __get_ingress_controller_external_ip(self):
        """
        Get External IP for Ingress Controller Load Balancer Service
        :return: External IP of Load Balancer
        """
        LOG.info("Getting external IP for Ingress Controller Service in cluster {0}".format(self.cluster_name))
        command = constants.COMMAND_GET_INGRESS_CONTROLLER_EXTERNAL_IP.format(constants.KUBECONFIG_PATH)
        command_output = utils.execute_command(command)

        json_obj = json.loads(command_output)
        external_ip = json_obj['status']['loadBalancer']['ingress'][0]['hostname']
        LOG.info("External IP for Ingress Controller Service = {0}".format(external_ip))
        return external_ip

    def _create_service_account_alb(self):
        """
        Create the AWS LB controller Service Account
        """
        LOG.info("Creating the service account for the aws load balancer controller {0}".format(self.cluster_name))
        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_AWS_ALB_CONTROLLER_SA_YAML)
        command = constants.COMMAND_KUBECTL_APPLY.format(template_path, constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)
        LOG.info("Service account created for the aws load balancer controller {0}".format(self.cluster_name))

        # Annotating the SA with EKS Role ARN
        aws_account_id = self.outputs[constants.AWS_ACCOUNT_ID]
        eks_role_arn = constants.EKS_ROLE_ARN.format(aws_account_id, self.environment_name)
        command = constants.COMMAND_KUBECTL_ANNOTATE.format(eks_role_arn, constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)
        LOG.info("Annotating the SA with EKS Role ARN done for loadbalancer controller in {0}".format(self.cluster_name))

    def _create_hosted_zone(self):
        """
        Create DNS Private Hosted Zone and create A records for IDUN hostnames
        :return:
        """
        LOG.info("Creating hosted zone for {0}".format(self.cluster_name))

        # Get ELB DNS Name from Ingress Controller
        elb_dns_name = str(self.__get_ingress_controller_external_ip())
        LOG.info("ELB DNS NAME = {0}".format(elb_dns_name))

        # Create Hosted Zone with Private DNS Name
        self.aws_r53client.create_hosted_zone(hosted_zone_name=self.hosted_zone_name,
                                              vpc_id=self.vpcid)

        LOG.info("Created hosted zone for {0}".format(self.cluster_name))

        LOG.info("Creating records in hosted zone {0}".format(self.hosted_zone_name))
        # For all hostnames, create record
        aws_account_id = self.outputs[constants.AWS_ACCOUNT_ID]
        self.aws_r53client.create_records(hosted_zone_name=self.hosted_zone_name,
                                          record_names=self.hostnames,
                                          elb_dns_name=elb_dns_name,
                                          account_id=aws_account_id)
        LOG.info("Created records in hosted zone {0}".format(self.hosted_zone_name))

    def _deploy_cluster_autoscaler(self):
        """
        Create IAM OIDC Federated Authentication and Deploy autoscaler app on EKS the cluster
        :return:
        """
        LOG.info("Deploying autoscaler and needed resources for {0}".format(self.cluster_name))

        #Create open_id_connect_provider
        cluster_config = self.aws_eksclient.describe_cluster(cluster_name=self.cluster_name)
        cluster_oid_url = str(cluster_config['cluster']['identity']['oidc']['issuer'])

        thumb_print =self._get_thumb_print(cluster_oid_url=cluster_oid_url)

        open_id_arn = self.aws_iamclient.create_open_id_connect_provider(oid_url=cluster_oid_url,
                                                                         thumb_print=thumb_print,
                                                                         env_name=self.environment_name)

        # Create policy for cluster_autoscaler in IAM
        autoscaler_iam_policy_name = constants.AUTOSCALER_IAM_POLICY.format(self.environment_name)
        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_AUTOSCALER_IAM_POLICY)
        policy_string = utils.load_json_string(json_file_path=template_path)
        policy_arn = self.aws_iamclient.create_policy(policy_name=autoscaler_iam_policy_name,
                                                      policy_string=policy_string,
                                                      env_name=self.environment_name)

        # Create Role for cluster_autoscaler in IAM
        template_path = os.path.join(constants.TEMPLATES_DIR, constants.TEMPLATE_AUTOSCALER_IAM_ROLE)

        if open_id_arn:
            open_identifier = open_id_arn.split('/')[3]
        else:
            open_id_arn = self._get_oid_arn(cluster_oid_url=cluster_oid_url,
                                               env_name=self.environment_name)
            open_identifier = open_id_arn.split('/')[3]

        if not policy_arn:
            policy_arn = self._get_policy_arn(autoscaler_iam_policy_name,
                                                 env_name=self.environment_name)

        role_string = utils.load_json_string(json_file_path=template_path)
        role_string = role_string.replace('OPENID_PROVIDER', open_id_arn)
        role_string = role_string.replace('IDENTIFIER', open_identifier)
        role_string = role_string.replace('AWS_REGION', self.aws_region)
        self.role_arn = self.aws_iamclient.create_role(role_name=self.autoscaler_iam_role,
                                                       role_string=role_string,
                                                       env_name=self.environment_name)

        # Attach Policy to Role
        self.aws_iamclient.attach_role_policy(role_name=self.autoscaler_iam_role, policy_arn=policy_arn)

        # deploy autoscaler app in kube-system namespace
        self._deploy_cluster_autoscaler_app()

        LOG.info("Deployed autoscaler and needed resources for {0}".format(self.cluster_name))

    def _deploy_cluster_autoscaler_app(self):
        """
        Deploy Cluster Auto Scaler deployment.apps to kube-system
        :return:
        """
        LOG.info("Deploying Cluster Autoscaler apps.deployment in EKS Cluster {0}".format(self.cluster_name))

        role_arn = self.role_arn
        if not role_arn:
            role_arn = self._get_role_arn(autoscaler_iam_role_name=self.autoscaler_iam_role,
                                             env_name=self.environment_name)
        LOG.info(f"self.role_arn={self.role_arn}    role_arn={role_arn}")

        substitutions = {
            "CLUSTER_NAME":     self.cluster_name,
            "AUTOSCALER_ROLE":  role_arn,
            "REGION_NAME":      self.config[constants.AWS_REGION],
            **self.registry_map
        }
        utils.kubectl_apply(constants.TEMPLATE_CLUSTER_AUTO_SCALER,substitutions)

        command = constants.COMMAND_CLUSTER_AUTOSCALER_SAFE_TO_EVICT.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        LOG.info("Deployed Cluster Autoscaler app")

    def _get_oid_arn(self, cluster_oid_url, env_name):
        oid_cluster = cluster_oid_url.split('/')[4]
        oid_arn_list = self.aws_iamclient.list_open_id_connect_providers(env_name)
        oid_arn_output = [x['Arn'] for x in oid_arn_list if oid_cluster in x['Arn']]
        open_id_arn = ' '.join(map(str, oid_arn_output))
        return open_id_arn

    def _get_policy_arn(self, autoscaler_iam_policy_name, env_name):
        policy_list = self.aws_iamclient.list_policies(env_name)
        policy_output = [x['Arn'] for x in policy_list if autoscaler_iam_policy_name in x['PolicyName']]
        policy_arn = ' '.join(map(str, policy_output))
        return policy_arn

    def _get_role_arn(self, autoscaler_iam_role_name, env_name):
        role_list = self.aws_iamclient.list_roles(env_name)
        role_output = [x['Arn'] for x in role_list if autoscaler_iam_role_name in x['RoleName']]
        role_arn = ' '.join(map(str, role_output))
        return role_arn

    def _get_thumb_print(self, cluster_oid_url):
        url = cluster_oid_url + '/' + '.well-known/openid-configuration'
        response = requests.get(url)
        response_jwks = response.json()['jwks_uri'].split('/')[2]
        response_jwks_str = json.dumps(response_jwks)
        command = constants.COMMAND_GET_CERTIFICATE.format(response_jwks_str, response_jwks_str)
        command_output = utils.execute_command(command=command)
        temp_filename = tempfile.mktemp()
        certificate = tempfile.mktemp()
        with open(temp_filename, 'w') as file:
            file.write(command_output)

        start_pattern = '^[-]+BEGIN CERTIFICATE[-]+'
        end_pattern = '^[-]+END CERTIFICATE[-]+'
        with open(temp_filename) as file:
            match = False
            newfile = None
            for line in file:
                if re.match(start_pattern, line):
                    match = True
                    newfile = open(certificate, 'w')
                    newfile.write(line)
                elif re.match(end_pattern, line):
                    match = False
                    newfile.write(line)
                    newfile.close()
                elif match:
                    newfile.write(line)

        command = constants.COMMAND_GET_FINGERPRINT.format(certificate)
        command_output = utils.execute_command(command)
        thumb_print = ''.join(command_output.split('=')[1].split(':'))
        return thumb_print.strip().lower()

    def _deploy_prometheus(self):
        """
        Deploy Prometheus
        """
        LOG.info("Deploying Prometheus in EKS Cluster {0}".format(self.cluster_name))

        LOG.info("Adding Prometheus Repo in Helm...")
        command = constants.COMMAND_PROMETHEUS_REPO_ADD.format(constants.KUBECONFIG_PATH)
        utils.execute_command(command=command)

        # Create Namespace
        LOG.info("Creating Prometheus Namespace...")
        utils.create_namespace(constants.PROM_NAMESPACE)

        # Install Prometheus
        LOG.info("Installing Prometheus...")
        prometheus_values, subs = self.__get_values_and_substitutions(constants.TEMPLATE_PROMETHEUS_VALUES)
        utils.exec_cmd(constants.COMMAND_INSTALL_PROMETHEUS,prometheus_values,subs)

        # Deploy Prometheus Ingress
        if 'prometheus' not in self.config[constants.HOSTNAMES]:
            raise Exception('The hostname for Prometheus is missing. Check config.yaml')
        prometheus_hostname = self.config[constants.HOSTNAMES]['prometheus']
        LOG.info('Prometheus hostname: ' + prometheus_hostname)
        utils.kubectl_apply(constants.TEMPLATE_PROMETHEUS_INGRESS,dict(PROMETHEUS_HOSTNAME=prometheus_hostname))

        LOG.info("Deployed Prometheus")

    def __get_values_and_substitutions(self, prometheus_values):
        subs = {
            'EIAP_NAMESPACE': self.eiap_namespace,
            **self.registry_map
        }

        if not self.is_ecn_connected:
            prom_values_data = utils.load_yaml(constants.TEMPLATES_DIR + '/' + prometheus_values)
            prom_values_data['serviceAccounts'] = {
                  'server': {
                    'create': True,
                    'name': self.ingest_service_account_name,
                    'annotations': {
                      'eks.amazonaws.com/role-arn': self.cfout[self.infra_add_stack_name]['AmpIngestRoleArn']
                    }
                  }
                }
            prom_values_data['server']['env'] = [{
                        'name': 'AWS_STS_REGIONAL_ENDPOINTS',
                        'value': 'regional'
                      }]
            prom_values_data['server']['remoteWrite'] = [{
                      'queue_config':{
                        'capacity': 2500,
                        'max_samples_per_send': 1000,
                        'max_shards': 200
                      },
                      'sigv4':{'region': self.aws_region},
                      'url': self.cfout[self.infra_add_stack_name]['AmpWorkspaceUrl'] + 'api/v1/remote_write'
                    }]

            utils.write_yaml(constants.TEMPLATES_DIR + '/' + constants.TEMPLATE_PROMETHEUS_PUBLIC_VALUES, prom_values_data)
            prometheus_values = constants.TEMPLATE_PROMETHEUS_PUBLIC_VALUES

        return prometheus_values, subs


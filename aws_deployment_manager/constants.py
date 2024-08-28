"""
Class to declare constant string values
"""
VERSION = "0.1.0"

# Config Property Names
ENVIRONMENT_NAME = "EnvironmentName"
AWS_REGION = "AWSRegion"
VPC_ID = "VPCID"
NUMBER_PRIVATE_SUBNETS = "NumPrivateSubnets"
CONTROL_PLANE_SUBNET_IDS = "ControlPlaneSubnetIds"
WORKER_NODE_SUBNET_IDS = "WorkerNodeSubnetIds"
PRIVATE_SUBNET_01_ID = "PrivateSubnet01Id"
PRIVATE_SUBNET_02_ID = "PrivateSubnet02Id"
PRIVATE_SUBNET_01_AZ = "PrivateSubnet01Az"
PRIVATE_SUBNET_02_AZ = "PrivateSubnet02Az"
PRIVATE_SUBNET_01_RT_ID = "PrivateRouteTable01"
PRIVATE_SUBNET_02_RT_ID = "PrivateRouteTable02"
MIN_NODES = "MinNodes"
DISK_SIZE = "DiskSize"
NODE_INSTANCE_TYPE = "NodeInstanceType"
MAX_NODES = "MaxNodes"
PRIMARY_VPC_CIDR = "PrimaryVpcCIDR"
SECONDARY_VPC_CIDR = "SecondaryVpcCIDR"
HOSTNAMES = 'Hostnames'
PRIVATE_DOMAIN_NAME = 'PrivateDomainName'
S3_URL = "S3URL"
DISABLE_PUBLIC_ACCESS = "DisablePublicAccess"
SSH_KEY_PAIR_NAME = "SshKeyPairName"
ARMDOCKER_USER = "Armdockeruser"
ARMDOCKER_PASS = "Armdockerpass"
NAMESPACE_K8S_DASHBOARD = "kubernetes-dashboard"
NAMESPACE_NGINX = "ingress-nginx"
NAMESPACE_KUBE_SYSTEM = "kube-system"
KUBE_DOWNSCALER = "KubeDownscaler"
K8S_VERSION = "K8SVersion"

# Backup Server Configuration
BACKUP_INSTANCE_TYPE = "BackupInstanceType"
BACKUP_AMI_ID = "BackupAmiId"
BACKUP_DISK = "BackupDisk"
BACKUP_SECURITY_GROUP = "BackupSecurityGroup"
BACKUP_PASS = "BackupPass"
BACKUP_SERVER_IP_FILENAME = "/workdir/backup_server_ip.properties"
USER_DATA = """#!/usr/bin/env bash
sudo mkfs -t xfs /dev/nvme1n1
mkdir /backup-data
chmod 777 /backup-data
mount /dev/nvme1n1 /backup-data/
useradd backup
chown backup /backup-data
echo -e "PASS\nPASS" | passwd backup
chage -M -1 backup
echo backup >> /etc/cron.allow
echo "0 1 * * * BACKUP_TO_KEEP=5; find /backup-data/*/DEFAULT/* -maxdepth 0 -type f | sort -r | tail -n +\$(expr \$BACKUP_TO_KEEP '*' 2 + 1) | xargs -r rm -f;" >> /var/spool/cron/backup
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
"""
BACKUP_SERVER="Backup Server"
OLD_VOLUME_LABEL='backup-server-volume-until-{0}'
OLD_BACKUP_LABEL='old backup server'
NAME='Name'

# Workdir and Config File Names
CONFIG_FILE_NAME = "config.yaml"
WORKDIR_PATH = "/workdir"
LOGS_DIRECTORY_NAME = "logs"
CONFIG_FILE_PATH = "/workdir/config.yaml"
LOGS_DIRECTORY_PATH = "/workdir/logs"
KUBECONFIG_PATH = "/workdir/config"
KUBECONFIG_NAME = "config"


# Cloudformation Templates
IDUN_BASE_DIR = "/idun"
TEMPLATES_DIR = "/idun/templates"
TEMPLATE_BASE_VPC = "IDUN_Base_VPC.yaml"
TEMPLATE_BASE_ADDITIONAL = "IDUN_Base_additional.yaml"
TEMPLATE_VPC = "IDUN_VPC.yaml"
TEMPLATE_INFRA_MASTER = "IDUN_Infra_Master.yaml"
TEMPLATE_INFRA_ADD = "IDUN_Infra_additional.yaml"
TEMPLATE_ALB_CONTROLLER = "IDUN_ALB_Controller.yaml"
TEMPLATE_CSI_CONTROLLER = "IDUN_EBS_CSI_Controller.yaml"
TEMPLATE_EKS_CLUSTER = "IDUN_EKS_Cluster.yaml"
TEMPLATE_AWS_AUTH_CM = "aws-auth-cm.yaml"
TEMPLATE_METRICS_SERVER = "metrics-server.yaml"
TEMPLATE_K8S_DASHBOARD = "kubernetes-dashboard.yaml"
TEMPLATE_EKS_ADMIN_SERVICE_ACCOUNT = "eks-admin-service-account.yaml"
TEMPLATE_POD_ENI_CONFIG = "pod-eniconfig-template.yaml"
TEMPLATE_GP2_STORAGE_CLASS = "gp2-storage-class.yaml"
TEMPLATE_GP3_STORAGE_CLASS = "gp3-storage-class.yaml"
TEMPLATE_CLUSTER_AUTO_SCALER = "cluster-autoscaler-autodiscover.yaml"
TEMPLATE_NGINX_CONTROLLER = "nginx-controller.yaml"
TEMPLATE_CONFIG_FILE = "idun_config_template.yaml"
TEMPLATE_KUBE_DOWNSCALER = "kube-downscaler.yaml"
TEMPLATE_EKS_VERSIONS = "eks_versions.yaml"
TEMPLATE_PROMETHEUS_INGRESS = "prometheus-ingress.yaml"
TEMPLATE_CSI_VALUES = "ebs-csi-driver_helmValues.yaml"
TEMPLATE_CSI_TEMPORARY = "ebs-csi-driver_temporary_k8s_objects.yaml"
TEMPLATE_PROMETHEUS_VALUES = "prometheus_helmValues.yaml"
TEMPLATE_PROMETHEUS_PUBLIC_VALUES = "prometheus_public_helmValues.yaml"
TEMPLATE_PROMETHEUS_TEMPORARY = "prometheus_temporary_k8s_objects.yaml"
TEMPLATE_CALICO_OPERATOR = "calico-operator.yaml"
TEMPLATE_CALICO_CRS = "calico-crs.yaml"
TEMPLATE_BLACKLIST = [TEMPLATES_DIR+'/ubuntu-deploy.yaml']
TEMPORARY_DIR = "/tmp"
TEMPLATE_AWS_ALB_CONTROLLER_SA_YAML = "aws-load-balancer-controller-service-account.yaml"

# AWS Access Keys
AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
AWS_DEFAULT_REGION = "AWS_DEFAULT_REGION"

# AWS Service Names
SUPPORTED_REGIONS = ["eu-west-1", "us-east-1"]
CLOUDFORMATION_SERVICE = 'cloudformation'
ROUTE53_SERVICE = 'route53'
ELB_SERVICE = 'elbv2'
EKS_SERVICE = 'eks'
S3_SERVICE = 's3'
EC2_SERVICE = 'ec2'
IAM_SERVICE = 'iam'
ASG_SERVICE = "autoscaling"

# General
MONITORING_HOST = "MONITORING_HOST"
NODEGROUP_NAME = "{0}-Node-Group-{1}-{2}"
AMI_TYPE = "AL2_x86_64"
ARMDOCKER_SECRET_NAME = "armdockersecret"
ARMDOCKER_REGISTRY_URL = "armdocker.seli.gic.ericsson.se"
CLUSTER_NAME_POSTFIX = "-EKS-Cluster"
ELB_ARN = "arn:aws:elasticloadbalancing:{0}:{1}:loadbalancer/net/{2}"
EKS_ROLE_ARN = "eks.amazonaws.com/role-arn=arn:aws:iam::{0}:role/{1}-AmazonEKSLoadBalancerControllerRole"
BASE_VPC_STACK_NAME = "idun-base-vpc"
BASE_ADDITIONAL_STACK_NAME = 'idun-base-additional'
IDUN_ADDITIONAL_SUFFIX_STACK_NAME = '-additional'
ALB_CONTROLLER_SUFFIX_STACK_NAME = '-alb-controller'
CSI_CONTROLLER_SUFFIX_STACK_NAME = '-ebs-csi-controller'
HTTP_OK = 200
STORAGE_CLASS_NAME_GP2 = "gp2"
STORAGE_CLASS_NAME_GP3 = "gp3"
BUCKET_POSTFIX = "-deployment-templates"
INGEST_SA_NAME__DEFUALT = 'amp-iamproxy-ingest-service-account'

# Commands
COMMAND_HELM_REPO_UPDATE = "helm repo update --kubeconfig {0}"
COMMAND_KUBECTL_UPDATE_CONFIG = "aws eks update-kubeconfig --name {0} --region {1} --kubeconfig {2} --output json"
COMMAND_KUBECTL_UPDATE_CM = "kubectl replace -f {0} --kubeconfig {1}"
COMMAND_KUBECTL_DESCRIBE_CM = "kubectl describe configmap aws-auth -n kube-system --kubeconfig {0}"
COMMAND_KUBECTL_APPLY = "kubectl apply -f {0} --kubeconfig {1}"
COMMAND_KUBECTL_DELETE = "kubectl delete -f {0} --kubeconfig {1}"
COMMAND_KUBECTL_ANNOTATE = "kubectl annotate serviceaccount -n kube-system aws-load-balancer-controller {0} " \
                           "--kubeconfig {1} "
COMMAND_GET_METRICS_SERVER = "kubectl get deployment metrics-server -n kube-system --kubeconfig {0}"
COMMAND_ENABLE_CUSTOM_CNI_CONFIG = "kubectl set env daemonset aws-node -n kube-system --kubeconfig {0} " \
                                   "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true"
COMMAND_SET_ENI_CONFIG_LABEL = "kubectl set env daemonset aws-node -n kube-system --kubeconfig {0} " \
                               "ENI_CONFIG_LABEL_DEF=failure-domain.beta.kubernetes.io/zone"
COMMAND_GET_STORAGECLASS = "kubectl get storageclass --kubeconfig {0}"
COMMAND_DELETE_STORAGECLASS = "kubectl delete storageclass {0} --kubeconfig {1}"
COMMAND_CLUSTER_AUTOSCALER_SAFE_TO_EVICT = "kubectl -n kube-system annotate deployment.apps/cluster-autoscaler " \
                                           "cluster-autoscaler.kubernetes.io/safe-to-evict=\"false\" --overwrite " \
                                           "--kubeconfig {0}"
COMMAND_GET_INGRESS_CONTROLLER_EXTERNAL_IP = "kubectl get svc -n ingress-nginx ingress-nginx-controller --output json" \
                                             " --kubeconfig {0}"
COMMAND_GET_NAMESPACES = "kubectl get namespace --kubeconfig {0}"
COMMAND_GET_PVCS = "kubectl get pvc -n {0} --kubeconfig {1}"
COMMAND_GET_HELM_DEPLOYMENTS = "helm ls -A --kubeconfig {0}"
COMMAND_DELETE_PVCS = "kubectl delete --all pvc -n {0} --kubeconfig {1}"
COMMAND_HELM_UNINSTALL_NO_HOOKS = "helm uninstall --no-hooks {0} -n {1} --kubeconfig {2}"
COMMAND_CREATE_ARMDOCKER_REGISTRY_SECRET = "kubectl create secret docker-registry {0} " \
                                           "--docker-server={1} " \
                                           "--docker-username={2} " \
                                           "--docker-password={3} " \
                                           "-n {4} " \
                                           "--kubeconfig {5}"
COMMAND_DELETE_ARMDOCKER_REGISTRY_SECRET = "kubectl delete secret {0} -n {1} --kubeconfig {2} --ignore-not-found"
COMMAND_CREATE_NAMESPACE = "kubectl create namespace {0} --kubeconfig {1}"
COMMAND_GET_ALL_NAMESPACES = "kubectl get namespace -A --kubeconfig {0}"
COMMAND_DELETE_AUTOSCALER = "kubectl delete deployment.apps/cluster-autoscaler -n kube-system --kubeconfig {0}"
COMMAND_GET_AUTOSCALER = "kubectl get deployment -l app=cluster-autoscaler -n kube-system --kubeconfig {0}"
COMMAND_GET_DOWNSCALER = "kubectl get deployment -l application=kube-downscaler -n kube-system --kubeconfig {0}"
COMMAND_DELETE_DOWNSCALER = "kubectl delete deployment.apps/kube-downscaler -n kube-system --kubeconfig {0}"
COMMAND_GET_FINGERPRINT = "openssl x509 -in {0} -fingerprint -noout"
COMMAND_GET_CERTIFICATE = "echo -n |openssl s_client -servername {0} -showcerts -connect {1}:443"

# IDUN Master Stack Output
PRIVATE_SUBNET_IDS = "PrivateSubnetIds"
SECURITY_GROUPS = "SecurityGroups"
EKS_CLUSTER_NAME = "EKSClusterName"
EKS_CLUSTER_ARN = "EKSClusterArn"
POD_SECURITY_GROUP = "PodSecurityGroupId"
POD_SUBNET_IDS = "PodSubnetIds"
POD_SUBNET_AZS = "PodSubnetAzs"
EBS_KMS_KEY_ARN = "EBSKMSKeyArn"
AWS_ACCOUNT_ID = "AWSAccountId"
NODE_ROLE_ARN = "NodeRoleArn"

# IDUN Base VPC Stack Output
ENDPOINT_SECURITY_GROUP_ID = "EndpointSecurityGroupId"

# IDUN Infra Additional Reources Stack
EKS_CLUSTER_OIDC = 'EKSClusterOIDC'
SERVICE_ACCOUNT_NAMESPACE = 'ServiceAccountNamespace'
INGEST_SERVICE_ACCOUNT_NAME = 'IngestServiceAccountName'

# AWS EBS CSI Controller Stack Output
CSI_CONTROLLER_ROLE_ARN = "CSIControllerRoleARN"


# Autoscaler requirements
TEMPLATE_AUTOSCALER_IAM_POLICY = "autoscaler_policy.json"
TEMPLATE_AUTOSCALER_IAM_ROLE = "autoscaler_role.json"
AUTOSCALER_IAM_ROLE = "{0}-AutoscalerRole"
AUTOSCALER_IAM_POLICY = "{0}-AutoscalerPolicy"

# Stage States
STAGE_STARTED = "started"
STAGE_FINISHED = "finished"
VALID_STATES = ["started", "finished"]

# Install Stages
INSTALL_STAGE_LOG_PATH = "/workdir/.install_stage.log"
INSTALL_STAGE_APPLY_EKS_TAGS = "install.apply.eks.tags"
INSTALL_STAGE_CREATE_BASE_VPC_STACK = "install.create.vpc.stack"
INSTALL_STAGE_CREATE_BASE_ADD_STACK = "install.create.additional.stack"
INSTALL_STAGE_UPDATE_ENDPOINT_SEC_GR = "install.update.endpoint.securitygroup"
INSTALL_STAGE_CREATE_IDUN_INFRA_STACK = "install.create.idun.infrastructure.stack"
INSTALL_STAGE_CREATE_IDUN_ADDIT_STACK = "install.create.idun.additional.stack"
INSTALL_STAGE_CREATE_ALB_CONTROLLER_STACK = "install.create.alb.controller.stack"
INSTALL_STAGE_CREATE_CSI_CONTROLLER_STACK = "install.create.csi.controller.stack"
INSTALL_STAGE_UPDATE_K8S_CONFIG_MAP = "install.update.config.map"
INSTALL_STAGE_CHANGE_CLUSTER_ACCESS = "install.change.cluster.access"
INSTALL_STAGE_UPDATE_CNI_VERSION = "install.update.cni.version"
INSTALL_STAGE_ENABLE_CNI_CONFIG = "install.enable.cni.config"
INSTALL_STAGE_CREATE_ENI_CONFIG = "install.create.eni.config"
INSTALL_STAGE_SET_ENI_LABEL = "install.set.eni.label"
INSTALL_STAGE_DEPLOY_CALICO_CNI = "install.deploy.calico.cni"
INSTALL_STAGE_CREATE_DEFAULT_STORAGE = "install.create.default.storage"
INSTALL_STAGE_CREATE_NODE_GROUP = "install.create.node.group"
INSTALL_STAGE_SETUP_K8S_DASHBOARD = "install.setup.k8s.dashboard"
INSTALL_STAGE_DEPLOY_EBS_CSI_CONTROLLER = "install.deploy.csi.controller"
INSTALL_STAGE_SETUP_NGINX_CONTROLLER = "install.setup.nginx.controller"
INSTALL_STAGE_SETUP_HOSTED_ZONE = "install.setup.hosted.zone"


# Configure Stages
CONFIGURE_STAGE_DEPLOY_NGINX_CONTROLLER = "configure.deploy.nginx.controller"
CONFIGURE_STAGE_CREATE_SA_ALB_CONTROLLER = "configure.create.service.account.alb"
CONFIGURE_STAGE_INSTALL_ALB_CONTROLLER = "configure.install.aws.lb.controller"
CONFIGURE_STAGE_CREATED_HOSTED_ZONE = "configure.create.hosted.zone"
CONFIGURE_STAGE_DEPLOY_AUTO_SCALER = "configure.deploy.auto.scaler"
CONFIGURE_STAGE_DEPLOY_KUBE_DOWNSCALER = "configure.deploy.kube.downscaler"
CONFIGURE_STAGE_DEPLOY_PROMETHEUS = "configure.deploy.prometheus"
CONFIGURE_STAGE_DEPLOY_GRAFANA = "configure.deploy.grafana"

# Cluster Upgrade
KUBE_PROXY = "KubeProxy"
CORE_DNS = "CoreDNS"
CNI_PLUGIN = "CNIPlugin"
AUTO_SCALER = "AutoScaler"
AWS_LB_CONTROLLER = "AWSLbController"
NODE_GROUPS_SECRET = "nodegroupssecret"
COMMAND_GET_UNHEALTHY_PODS = "kubectl get pod -A --kubeconfig {0} | grep -v -e Run -e Compl -e Succ"
COMMAND_GET_KUBE_PROXY_IMAGE = "kubectl get daemonset kube-proxy --namespace kube-system " \
                               "-o=jsonpath='{$.spec.template.spec.containers[:1].image}'"
COMMAND_SET_KUBE_PROXY_IMAGE = "kubectl set image daemonset.apps/kube-proxy -n kube-system kube-proxy={0} " \
                               "--kubeconfig {1}"
COMMAND_GET_CORD_DNS_IMAGE = "kubectl get deployment coredns --namespace kube-system " \
                             "-o=jsonpath='{$.spec.template.spec.containers[:1].image}'"
COMMAND_SET_CORE_DNS_IMAGE = "kubectl set image --namespace kube-system deployment.apps/coredns coredns={0} " \
                             "--kubeconfig {1}"
COMMAND_GET_AUTO_SCALER_IMAGE = "kubectl get deployment cluster-autoscaler --namespace kube-system " \
                                "-o=jsonpath='{$.spec.template.spec.containers[:1].image}'"
COMMAND_SET_AUTO_SCALER_IMAGE = "kubectl set image --namespace kube-system deployment.apps/cluster-autoscaler " \
                                "cluster-autoscaler={0} --kubeconfig {1}"
COMMAND_GET_NODES = "kubectl get no --kubeconfig {0}"
COMMAND_CORDON_NODE = "kubectl cordon {0} --kubeconfig {1}"
COMMAND_UNCORDON_NODE = "kubectl uncordon {0} --kubeconfig {1}"
COMMAND_DRAIN_NODE = "kubectl drain --ignore-daemonsets --grace-period=120 --timeout=1800s --delete-emptydir-data " \
                     "--force {0} --kubeconfig {1}"
COMMAND_CREATE_NODE_GROUPS_SECRET = "kubectl create secret generic {0} " \
                                           "--from-literal=nodegroups={1} " \
                                           "--from-literal=nodes={2} " \
                                           "--kubeconfig {3}"
COMMAND_DELETE_NODE_GROUPS_SECRET = "kubectl delete secret {0} --kubeconfig {1} --ignore-not-found"
COMMAND_GET_NODE_GROUPS_SECRET = "kubectl get secret {0} -o jsonpath={{.data.nodegroups}} --kubeconfig {1} " \
                                          "| base64 -d"
COMMAND_GET_NODES_SECRET = "kubectl get secret {0} -o jsonpath={{.data.nodes}} --kubeconfig {1} " \
                                          "| base64 -d"
COMMAND_STOP_CLUSTER_AUTOSCALER = "kubectl scale deploy cluster-autoscaler --replicas=0 -n kube-system " \
                                  "--kubeconfig {0}"
COMMAND_START_CLUSTER_AUTOSCALER = "kubectl scale deploy cluster-autoscaler --replicas=1 -n kube-system " \
                                   "--kubeconfig {0}"

# AWS EBS CSI Driver Setup
CSI_HELM_REPO_ADD = \
    "helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver"

CSI_HELM_COMMAND = \
    "helm --namespace kube-system " \
    "{0} " \
    "aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver --version='2.19.0' "
CSI_HELM_TEMPLATE = CSI_HELM_COMMAND.format("template ") + "--values {0}"
CSI_HELM_UPGRADE_INSTALL = CSI_HELM_COMMAND.format("upgrade --install") + "--values {0} --kubeconfig {1}"

# Prometheus and Grafana Setup
PROM_NAMESPACE='prometheus'
COMMAND_PROMETHEUS_HELM_REPO_ADD = \
    "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts "
COMMAND_PROMETHEUS_REPO_ADD = COMMAND_PROMETHEUS_HELM_REPO_ADD + "--kubeconfig {0}"
COMMAND_GRAFANA_REPO_ADD = "helm repo add grafana https://grafana.github.io/helm-charts --kubeconfig {0}"
COMMAND_GET_PROMETHEUS_TEMPLATE = "helm --namespace " + PROM_NAMESPACE + " template prometheus prometheus-community/prometheus " \
                                  " --version='18.1.1' --values {0}"
COMMAND_INSTALL_PROMETHEUS = "helm install prometheus prometheus-community/prometheus --namespace " + PROM_NAMESPACE + " " \
                             " --values {0} --kubeconfig {1} --version='18.1.1'"

# Calico CNI Setup
COMMAND_INSTALL_CALICO = "kubectl apply --kubeconfig {0} -f {1}"

#AWS Loadbalancer controller setup
COMMAND_ALB_CONTROLLER_REPO_ADD = "helm repo add eks https://aws.github.io/eks-charts"
COMMAND_INSTALL_ALB_CONTROLLER = \
    "helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller " \
                                 "-n kube-system " \
                                 "--set clusterName={0} " \
                                 "--set serviceAccount.create=false " \
                                 "--set serviceAccount.name=aws-load-balancer-controller " \
                                 "--set image.repository=602401143452.dkr.ecr.{" \
                                 "1}.amazonaws.com/amazon/aws-load-balancer-controller " \
                                 "--set image.tag={2} " \
                                 "--kubeconfig {3}"
COMMAND_UPGRADE_ALB_CONTROLLER=COMMAND_INSTALL_ALB_CONTROLLER
COMMAND_INSTALL_TGB_CRD = 'kubectl --kubeconfig {0} apply -k ' \
                          '"github.com/aws/eks-charts/stable/aws-load-balancer-controller/crds?ref=master" '
# COMMAND_INSTALL_TGB_CRD to install the TargetGroupBinding custom resource definitions:
#     https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html

# Registry
ARMDOCKER_RND="armdocker.rnd.ericsson.se"
ARMDOCKER_GIC="armdocker.seli.gic.ericsson.se"
EIAPAAS_REGISTRY=ARMDOCKER_GIC+"/proj-idun-aas"
QUAY_REGISTRY="quay.io"
DKRHUB_REGISTRY="docker.io"
K8SGCR_REGISTRY="k8s.gcr.io"

# Fix for test because LocalStack does not fully support EKS (cannot generate proper OIDC)
DUMMY_REPLACEMENT='DUMMY1111111CLUSTER111111111OIDC'

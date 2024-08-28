#!/bin/bash
# ********************************************************************
# Ericsson Radio Systems AB                                     SCRIPT
# ********************************************************************
#
#
# (c) Ericsson Radio Systems AB 2020 - All rights reserved.
#
# The copyright to the computer program(s) herein is the property
# of Ericsson Radio Systems AB, Sweden. The programs may be used
# and/or copied only with the written permission from Ericsson Radio
# Systems AB or in accordance with the terms and conditions stipulated
# in the agreement/contract under which the program(s) have been
# supplied.
#
#
# ********************************************************************
# Name      : idun_install.sh
# Date      :
# Revision  : PA1
# Purpose   : Script to install IDUN from Helm Charts
#
#
#
######################################################################

#VARIABLES
ECHO="/usr/bin/echo"
KUBECTL="/usr/local/bin/kubectl"
YQ="/usr/local/bin/yq"
HELM="/usr/local/bin/helm"
AWS_IAM_AUTHENTICATOR="/workdir/aws-iam-authenticator"
DOCKER="/usr/bin/docker"

#######################################################
# Removes the file and directories which were created #
# during the execution of this file.                  #
#                                                     #
# Arguments: int (0 or 1)                             #
# Returns: None                                       #
#######################################################
function cleanup_and_exit()
{
    ${ECHO} "Cleanup Started...."
    ${ECHO} "Cleanup done. Exiting..."
    exit ${1}
}

#######################################################
# Checks if mandatory files exist                     #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function check_mandatory_files_exist()
{
    if [ ! -f ${kubeconfig_path} ]
    then
        ${ECHO} "ERROR: Kubeconfig File must exist. Not found ${kubeconfig_path}"
        cleanup_and_exit 1
    else
        ${ECHO} "Kubeconfig File found ${kubeconfig_path}"
    fi

    if [ ! -f ${chart_path} ]
    then
        ${ECHO} "ERROR: IDUN Helm Charts must exist. Not found ${chart_path}"
        cleanup_and_exit 1
    else
        ${ECHO} "IDUN Helm Charts found ${chart_path}"
    fi

    if [ ! -f ${chart_values_path} ]
    then
        ${ECHO} "ERROR: IDUN Helm Charts Values must exist. Not found ${chart_values_path}"
        cleanup_and_exit 1
    else
        ${ECHO} "DUN Helm Charts Values found ${chart_values_path}"
    fi

    if [ ! -f ${AWS_IAM_AUTHENTICATOR} ]
    then
        ${ECHO} "ERROR: AWS IAM Authenticator Binary files must exist. Not found ${AWS_IAM_AUTHENTICATOR}"
        cleanup_and_exit 1
    fi
}

#######################################################
# Create Namespace                                    #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function create_namespace()
{
    ${ECHO} "Creating namespace..."
    ${KUBECTL} create namespace ${namespace} --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created namespace"
}

#######################################################
# Create Armdocker Pull Secret                        #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function create_armdocker_registry_secret()
{
    ${ECHO} "Creating Armdocker Registry Secret..."
    registry_secret=`${YQ} -r .global.registry.pullSecret ${chart_values_path}`
    registry_url=`${YQ} -r .global.registry.url ${chart_values_path}`
    registry_username=`${YQ} -r .global.registry.username ${chart_values_path}`
    registry_password=`${YQ} -r .global.registry.password ${chart_values_path}`
    
    # Check that docker login works
    ${DOCKER} login -u ${registry_username} -p ${registry_password} ${registry_url}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi

    ${KUBECTL} create secret docker-registry ${registry_secret} \
        --namespace=${namespace} \
        --docker-server=${registry_url} \
        --docker-username=${registry_username} \
        --docker-password=${registry_password} \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created Armdocker Registry Secret"
}

#######################################################
# Create PG Database Secret                           #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function create_database_pg_secret()
{
    ${ECHO} "Creating PG Database Secret..."
    ${KUBECTL} create secret generic eric-eo-database-pg-secret \
        --namespace=${namespace} \
        --from-literal=custom-user='customuser' \
        --from-literal=custom-pwd='Ericsson' \
        --from-literal=super-user='postgres' \
        --from-literal=super-pwd='Ericsson' \
        --from-literal=metrics-user='metricsuser' \
        --from-literal=metrics-pwd='Ericsson' \
        --from-literal=replica-user='replicauser' \
        --from-literal=replica-pwd='Ericsson' \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created PG Database Secret"
}

#######################################################
# Create Access Management Credentials Secret         #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function create_access-mgmt-creds()
{
    ${ECHO} "Creating Access Management Credentials Secret..."
    ${KUBECTL} create secret generic eric-sec-access-mgmt-creds \
        --namespace=${namespace} \
        --from-literal=kcadminid='kcadmin' \
        --from-literal=kcpasswd='Ericsson' \
        --from-literal=pgpasswd='Ericsson' \
        --from-literal=pguserid='pguser' \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created Access Management Credentials Secret"
}

#######################################################
# Create IAM CA Cert Secret                           #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function create_iam_ca_cert()
{
    ${ECHO} "Creating IAM CA Cert Secret..."
    ${KUBECTL} create secret generic iam-cacert-secret \
        --namespace=${namespace} \
        --from-file=tls.crt=${certificates_dir}/"intermediate-ca.crt" \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created IAM CA Cert Secret"
}

#######################################################
# Create TLS Secret                                   #
#                                                     #
# Arguments: Host                                     #
# Returns: None                                       #
#######################################################
function create_tls_secret()
{
    host=${1}
    secret_name=${host}"-tls-secret"
    crt_file=`${YQ} -r .global.hosts.${host} ${chart_values_path}`".crt"
    key_file=`${YQ} -r .global.hosts.${host} ${chart_values_path}`".key"

    ${ECHO} "Creating TLS Secret for ${host}..."
    ${ECHO} "Certificate file name ${crt_file}"
    ${ECHO} "Key file name ${key_file}"
    ${KUBECTL} create secret tls ${secret_name} \
        --namespace=${namespace} \
        --cert=${certificates_dir}/${crt_file} \
        --key=${certificates_dir}/${key_file} \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Created TLS Secret for ${host}"
}

#######################################################
# Install IDUN using Helm                             #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function helm_install()
{
    ${ECHO} "Installing IDUN via Helm..."
    ${HELM} install \
        ${deployment_name}-${namespace} \
        ${chart_path} \
        --namespace=${namespace} \
        --debug \
        --wait \
        --timeout 4800s \
        --values ${chart_values_path} \
        --kubeconfig ${kubeconfig_path}
    if [[ $? -ne 0 ]];then
        cleanup_and_exit 1
    fi
    ${ECHO} "Installed IDUN via Helm"
}

#######################################################
# Function to display the usage of this script        #
#                                                     #
# Arguments: None                                     #
# Returns: None                                       #
#######################################################
function display_usage ()
{
    ${ECHO} ""
    ${ECHO} -e "\tUsage:"
    ${ECHO} -e "\t====================================="
    ${ECHO} -e "\t./idun_install.sh <deployment_name> <namespace> <workdir> <chart_path> <chart_values_path>"
    ${ECHO} ""
    cleanup_and_exit 1
}

# Start
# Check if arguments have been passed
if [ "$#" -eq 5 ]
then
    deployment_name=${1}
    namespace=${2}
    workdir=${3}
    chart_path=${4}
    chart_values_path=${5}
    kubeconfig_path=${workdir}/kube_config/config
    certificates_dir=${workdir}/certificates
else
    ${ECHO} ""
    ${ECHO} "ERROR: Arguments mismatch. Please check the usage."
    display_usage
fi

# Check that mandatory files exist
check_mandatory_files_exist

# Create Namespace
create_namespace

# Create Armdocker Registry Pull Secret
create_armdocker_registry_secret

# Create PG Database Secret
create_database_pg_secret

# Create Access Management Credentials
create_access-mgmt-creds

 # Create IAM Intermeidate CA Cert
create_iam_ca_cert

 # Create TLS Secret
create_tls_secret iam
create_tls_secret so
create_tls_secret pf
create_tls_secret uds

# Helm Install IDUN
helm_install
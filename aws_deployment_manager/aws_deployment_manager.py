"""This is the initial python script for the deployment-manager."""

import sys
import logging
import time
import traceback
from datetime import timedelta
import getpass
import click
from aws_deployment_manager import utils, constants
from aws_deployment_manager.workdir import Workdir
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.install import InstallManager
from aws_deployment_manager.commands.update import UpdateManager
from aws_deployment_manager.commands.validate import ValidateManager
from aws_deployment_manager.commands.generate import GenerateManager
from aws_deployment_manager.commands.prepare import PrepareManager
from aws_deployment_manager.commands.getconfig import GetconfigManager
from aws_deployment_manager.commands.initialize import InitManager
from aws_deployment_manager.commands.configure import ConfigureManager
from aws_deployment_manager.commands.upgrade import UpgradeManager
from aws_deployment_manager.commands.rollback import RollbackManager
from aws_deployment_manager.commands.cleanup import CleanupManager
from aws_deployment_manager.commands.backup import BackupManager
from aws_deployment_manager.commands.image import ImageManager

LOG = logging.getLogger(__name__)


def log_verbosity_option(func):
    """A decorator for the log verbosity command line argument."""
    return click.option('-v', '--verbosity', type=click.IntRange(0, 4), default=3, show_default=True,
                        help='number for the log level verbosity, 0 lowest, 4 highest'
                        )(func)


def username_option(func):
    """A decorator for the user name command line argument."""
    return click.option('-u', '--username', type=click.STRING, required=False,
                        help='User Name for Armdocker Registry'
                        )(func)


def password_option(func):
    """A decorator for the password command line argument."""
    return click.option('-p', '--password', type=click.STRING, required=False,
                        help='User Name for Armdocker Registry'
                        )(func)


def environment_name_option(func):
    """A decorator for the IDUN Environment Name command line argument."""
    return click.option('-e', '--env', type=click.STRING, required=True,
                        help='Name for IDUN Environment'
                        )(func)


def namespace_option(func):
    """A decorator for the IDUN Namespace command line argument."""
    return click.option('-n', '--namespace', type=click.STRING, required=True,
                        help='Name of the namespace where IDUN will be installed'
                        )(func)


def aws_region_option(func):
    """A decorator for the AWS Region Name command line argument."""
    return click.option('-r', '--region', type=click.STRING, required=True,
                        help='AWS Region'
                        )(func)

def optional_aws_region_option(func):
    """A decorator for the AWS Region Name command line argument."""
    return click.option('-r', '--region', type=click.STRING, required=False,
                        default=None, help='AWS Region'
                        )(func)

def optional_parameters(func):
    """A decorator for the optional additional parameters to the command."""
    return click.option('-a', '--params', type=click.STRING, required=False,
                        default=None, help='additional parameters'
                        )(func)

def override_option(func):
    """A decorator for the override option command line argument."""
    return click.option('-o', '--override', type=click.BOOL, is_flag=True,
                          required=False, help='Override existing IDUN Configuration File'
                          )(func)

def yes_option(func):
    """A decorator for the yes option command line argument."""
    return click.option('-y', '--yes', type=click.BOOL, is_flag=True,
                          required=False, help='Confirmation to execute command'
                          )(func)

def force_option(func):
    """A decorator to force the push-image command."""
    return click.option('-f', '--force', type=click.BOOL, is_flag=True,
                          required=False, default=False,
                          help='Force the execution of the command even if the environment is connected to the Ericsson Network (DisablePublicAccess=False in config.yaml)'
                          )(func)

def command_option(func):
    """A decorator for the user name command line argument."""
    return click.option('-c', '--command', type=click.STRING, required=True,
                        help='Command to execute'
                        )(func)

def upgrade_kube_downscaler_option(func):
    """A decorator for the upgrade_kube_downscaler option command line argument."""
    return click.option('-g', '--upgrade-kube-downscaler', type=click.BOOL, is_flag=True,
                          required=False, default=False,
                          help='Enable the upgrade of kube-downscaler'
                          )(func)




@click.group(context_settings=dict(terminal_width=220))
def cli():
    """The IDUN AWS Deployment Manager."""


@cli.command()
@log_verbosity_option
def init(verbosity):
    """Initialize AWS Deployment Service for IDUN Install"""
    utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='init')
    InitManager().init()


@cli.command()
@log_verbosity_option
@override_option
def prepare(verbosity, override):
    """Generate Configuration File Template for installing IDUN in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='prepare')
    if not override:
        override = False
    LOG.info('Generating IDUN Config template...')
    LOG.info("Override Property Set = {0}".format(override))
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        file_path = PrepareManager(override=override).prepare_config_file()
        LOG.info("IDUN Config Template file generate at {0}".format(file_path))
    except Exception as exception:
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Config.yaml Preparation Finished')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@environment_name_option
@aws_region_option
def generate(verbosity, env, region):
    """Generate Configuration File from existing IDUN AWS deployment"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='generate')
    LOG.info('IDUN Config.yaml prepare Started for IDUN Deployment {0} in AWS Region {1}'.format(env, region))
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        GenerateManager(env_name=env, region=region).generate_config_file()
    except Exception as exception:
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Config.yaml Preparation Finished')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
def validate(verbosity):
    """Validate IDUN Configuration File"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='validate')
    LOG.info('IDUN Config Validation Started')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        ValidateManager().validate_config()
    except Exception as exception:
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Config Validation Finished')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
@username_option
@password_option
def install(verbosity, yes, username, password):
    """Install IDUN Infrastructure in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory, filename_postfix='install')
    LOG.info('IDUN AWS install started')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        question = "\nAre you sure you want to proceed with installation of IDUN Deployment"
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            armdocker_user = check_and_ask_username_option(username=username)
            armdocker_pass = check_and_ask_password_option(password=password)

            # Test Connection to Docker Registry
            utils.test_docker_registry_login(constants.ARMDOCKER_REGISTRY_URL, armdocker_user, armdocker_pass)

            install_manager = InstallManager(armdocker_user, armdocker_pass)

            # Execute Pre-Install Steps
            install_manager.pre_install()

            # Execute Install Steps
            install_manager.install()

            # Execute Post Install Steps
            install_manager.post_install()
        else:
            LOG.info("Aborting install operation...")
    except Exception as exception:
        LOG.error('IDUN AWS install failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN AWS install completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
@namespace_option
def configure(verbosity, yes, namespace):
    """Configure IDUN Infrastructure in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='configure')
    LOG.info('IDUN Configuration started')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        question = "\nAre you sure you want to proceed with configuration of IDUN Deployment"
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            # Configure IDUN
            config_manager = ConfigureManager(namespace)
            config_manager.configure()
        else:
            LOG.info("Aborting configuration operation...")
    except Exception as exception:
        LOG.error('IDUN Configuration failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Configuration completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
@upgrade_kube_downscaler_option
def upgrade(verbosity, yes, upgrade_kube_downscaler):
    """Upgrade IDUN AWS Infrastructure to latest K8S Version"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory, filename_postfix='upgrade')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        config = utils.load_yaml(file_path=constants.CONFIG_FILE_PATH)
        question = "\nAre you sure you want to upgrade IDUN Deployment {0} in region {1}".\
            format(config[constants.ENVIRONMENT_NAME], config[constants.AWS_REGION])
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            LOG.info("Proceeding with upgrade operation...")
            UpgradeManager().upgrade(upgrade_kube_downscaler)
        else:
            LOG.info("Aborting upgrade operation...")
    except Exception as exception:
        LOG.error('IDUN upgrade failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN upgrade completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
def rollback(verbosity, yes):
    """Rollback IDUN AWS Infrastructure to previous K8S Version"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='rollback')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        config = utils.load_yaml(file_path=constants.CONFIG_FILE_PATH)
        question = "\nAre you sure you want to rollback IDUN Deployment {0} in region {1}".\
            format(config[constants.ENVIRONMENT_NAME], config[constants.AWS_REGION])
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            LOG.info("Proceeding with rollback operation...")
            RollbackManager().rollback()
        else:
            LOG.info("Aborting rollback operation...")
    except Exception as exception:
        LOG.error('IDUN rollback failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN rollback completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
def cleanup(verbosity, yes):
    """Cleanup IDUN AWS Infrastructure after K8S Version Upgrade"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='cleanup')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        config = utils.load_yaml(file_path=constants.CONFIG_FILE_PATH)
        question = "\nAre you sure you want to cleanup IDUN Deployment {0} in region {1}".\
            format(config[constants.ENVIRONMENT_NAME], config[constants.AWS_REGION])
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            LOG.info("Proceeding with cleanup operation...")
            CleanupManager().cleanup()
        else:
            LOG.info("Aborting cleanup operation...")
    except Exception as exception:
        LOG.error('IDUN cleanup failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN cleanup completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
def update(verbosity, yes):
    """Update IDUN Infrastructure in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory, filename_postfix='update')
    LOG.info('IDUN AWS update started')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        question = "\nAre you sure you want to proceed with upgrade of IDUN Deployment"
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            UpdateManager().update()
        else:
            LOG.info("Aborting update operation...")
    except Exception as exception:
        LOG.error('IDUN AWS update failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN AWS update completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@environment_name_option
@aws_region_option
@yes_option
def delete(verbosity, env, region, yes):
    """Delete IDUN Infrastructure in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory, filename_postfix='delete')
    LOG.info('Delete started for IDUN Deployemnt {0} in region {1}'.format(env, region))
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        question = "\nAre you sure you want to delete IDUN Deployment {0} in region {1}".\
            format(env, region)
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            LOG.info("Proceeding with delete operation...")
            DeleteManager(env_name=env, region=region).delete()
        else:
            LOG.info("Aborting delete operation...")
    except Exception as exception:
        LOG.error('IDUN AWS delete failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN AWS delete completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@environment_name_option
@aws_region_option
def getconfig(verbosity, env, region):
    #def getconfig(verbosity, env, region):
    """Get Kubectl Config for IDUN Deployment in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='getconfig')
    LOG.info('IDUN Get Config started for deployment {0} in region {1}'.format(env, region))
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        getconfig_manager = GetconfigManager(env_name=env, region=region)
        getconfig_manager.generate_k8s_config_file()
    except Exception as exception:
        LOG.error('IDUN Get Config failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Get Config completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@command_option
def run(verbosity, command):
    """Run Command"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory, filename_postfix='run')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        LOG.info('Executing Command = {0}'.format(command))
        utils.execute_command(command=command)
    except Exception as exception:
        LOG.error('Failed to execute command')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('Command Executed Successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


@cli.command()
@log_verbosity_option
@yes_option
@optional_parameters
def configurebackup(verbosity, params, yes):
    """Configure External IDUN Backup server Infrastructure in AWS"""
    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='configure')
    LOG.info('IDUN Backup Server Install and configuration started')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        question = "\nAre you sure to proceed with backup Server configuration of IDUN Deployment"
        reply = check_and_ask_confirm_option(user_input=yes, question=question)

        if reply in ['y', 'yes']:
            # Configure IDUN Backup server
            if params and params.startswith("ami"):
                backup_manager = BackupManager()
                backup_manager.update_ami(params)
            else:
                backup_manager = BackupManager()
                backup_manager.backup_configure()
        else:
            LOG.info("Aborting configuration operation...")
    except Exception as exception:
        LOG.error('IDUN Backup Server Configuration failed with the following error')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('IDUN Backup Server Configuration completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)


def check_and_ask_confirm_option(user_input, question):
    """
    Checks if confirmation has been provided as CLI argument. If not, ask user for input
    :param user_input: CLI input
    :param question: Question to ask user
    :return: User Confirmation
    """
    if user_input:
        LOG.info("Confirmation provided as command argument")
        reply = 'yes'
    else:
        # Ask for User Confirmation
        reply = None
        while reply not in ['y', 'n', 'yes', 'no']:
            reply = str(input(question + ' (y/n): ')).lower().strip()

    return reply


def check_and_ask_username_option(username):
    """
    Checks if username has been provided as CLI argument. If not, ask user for input
    :param username: CLI input
    :return: Username
    """
    if username:
        LOG.info("Username for Armdocker Container Registry provided as command line argument")
        armdocker_user = str(username)
    else:
        question = "Please enter username for Armdocker Container Registry ({0}): ". \
            format(constants.ARMDOCKER_REGISTRY_URL)
        armdocker_user = str(input(question))

    return armdocker_user


def check_and_ask_password_option(password):
    """
    Checks if password has been provided as CLI argument. If not, ask user for input
    :param password: CLI input
    :return: Password
    """
    if password:
        LOG.info("Password for Armdocker Container Registry provided as command line argument")
        armdocker_pass = str(password)
    else:
        question = "Please enter password for Armdocker Container Registry ({0}): ". \
            format(constants.ARMDOCKER_REGISTRY_URL)
        armdocker_pass = getpass.getpass(prompt=question)

    return armdocker_pass

@cli.command('image-push')
@log_verbosity_option
@optional_aws_region_option
@force_option
def image_push(verbosity, region, force):
    """
    Pull the images from armdocker and push to ECR
    """

    log_file_path = utils.initialize_logging(verbosity=verbosity, working_directory=Workdir().workdir_path,
                                             logs_sub_directory=Workdir().logs_subdirectory,
                                             filename_postfix='image')
    LOG.info('Logging to %s', log_file_path)
    start_time = time.time()

    exit_code = 0
    try:
        image_manager = ImageManager(aws_image_region=region)
        image_manager.image(force)
    except Exception as exception:
        LOG.error('Push Image failed')
        LOG.debug(traceback.format_exc())
        LOG.error(exception, exc_info=True)
        LOG.info('Please refer to the following log file for further output: %s', log_file_path)
        exit_code = 1
    else:
        LOG.info('Push Image task completed successfully')
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        LOG.info('Time Taken: %s', timedelta(seconds=round(time_taken)))
        sys.exit(exit_code)

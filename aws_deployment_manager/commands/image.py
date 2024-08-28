"""
This module implements 'image' command
"""

import logging
import base64
import docker
import boto3

from aws_deployment_manager.commands.base import Base
from aws_deployment_manager import constants
from aws_deployment_manager import utils
from aws_deployment_manager import yamlhelper

LOG = logging.getLogger(__name__)


class ImageManager(Base):
    """ Main Class for 'image' command """

    def __init__(self, aws_image_region=None):
        Base.__init__(self)
        if aws_image_region is not None:
            # override of self.aws_region from config.yaml (see Base.__init__)
            self.aws_region = aws_image_region

        session = boto3.Session(region_name=self.aws_region)
        self._ecr = session.client('ecr')

        self._docker_client = docker.from_env(timeout=int(600))


    def image(self, force):
        """Pull the images from armdocker and push to ECR"""
        if not force and self.is_ecn_connected:
            LOG.info("The environment is connected to the Ericsson Network (DisablePublicAccess=False in the config.yaml), so the execution of push-image will be skipped.")
            LOG.info("To force the execution use the command line parameter --force.")
            return

        _generate_templates_from_helm_charts()
        images = yamlhelper.get_image_from_template(
            foldername=constants.TEMPLATES_DIR,
            blacklist=constants.TEMPLATE_BLACKLIST)
        LOG.info(f'Found {len(images)} images')
        self._create_repo_in_aws_ecr_if_required(images)
        ecn_images = _substitute_registry(images, self._get_ecn_registry_map())
        aws_images = _substitute_registry(images, self._get_aws_registry_map())
        LOG.info(f'ecn_images={ecn_images}')
        LOG.info(f'aws_images={aws_images}')
        self._login_ecr(self.aws_ecr_registry, self._ecr)
        self._push_images(ecn_images, aws_images)
        self._docker_client.close()


    def _login_ecr(self, aws_ecr_registry, ecr):
        """Login to ECR, obtain token and make docker login"""
        auth = ecr.get_authorization_token()
        token = auth["authorizationData"][0]["authorizationToken"]
        username, password = base64.b64decode(token).decode('ascii').split(':')
        self._docker_client.login(username=username, password=password, registry=aws_ecr_registry)


    def _push_images(self, ecn_images, aws_images):
        """Push images to ECR registry"""
        for ecn_image, aws_image in zip(ecn_images,aws_images):
            LOG.info(f"Image to pull:  {ecn_image}")
            LOG.info(f"Image to push:  {aws_image}")
            self._docker_client.images.pull(**_image_as_dict(ecn_image))
            self._docker_client.images.get(ecn_image).tag(**_image_as_dict(aws_image))
            output = self._docker_client.images.push(**_image_as_dict(aws_image), stream=True, decode=True)
            LOG.debug('Output of the docker push command')
            for line in output:
                LOG.debug(line)
            LOG.info("Image successfully processed")
        LOG.info("All images has been pulled and pushed")


    def _create_repo_in_aws_ecr_if_required(self, images):
        for img in images:
            repo_name = _extract_repo_name(img)
            create_repo = False
            try:
                LOG.info(f'Check if repo {repo_name} already exist in AWS')
                self._ecr.describe_repositories(repositoryNames=[repo_name])
            except Exception as exception:
                try:
                    if exception.response['Error']['Code'] == 'RepositoryNotFoundException':
                        create_repo = True
                except:
                    raise exception
            if create_repo:
                LOG.info(f'Create repo {repo_name} in AWS')
                self._ecr.create_repository(repositoryName=repo_name)


def _image_as_dict(image_str):
    """split the string repository:tag in a dictionary with fields 'repository' and 'tag'"""
    repository, tag = image_str.split(':')
    return dict(repository=repository, tag=tag)


def _generate_templates_from_helm_charts():

    helm_charts = [
        {
            "name": "prometheus",
            "repo": constants.COMMAND_PROMETHEUS_HELM_REPO_ADD,
            "val":  constants.TEMPLATE_PROMETHEUS_VALUES,
            "tmpl": constants.COMMAND_GET_PROMETHEUS_TEMPLATE,
            "yaml": constants.TEMPLATE_PROMETHEUS_TEMPORARY
        },
        {
            "name": "csi-driver",
            "repo": constants.CSI_HELM_REPO_ADD,
            "val":  constants.TEMPLATE_CSI_VALUES,
            "tmpl": constants.CSI_HELM_TEMPLATE ,
            "yaml": constants.TEMPLATE_CSI_TEMPORARY
        }
    ];
    for chart in helm_charts:
        utils.execute_command(command=chart['repo'])
        command = chart['tmpl'].format(constants.TEMPLATES_DIR + '/' + chart['val'])
        template = utils.execute_command(command=command)

        filename = constants.TEMPLATES_DIR + '/' + chart['yaml']
        with open(filename, 'w') as template_file:
            template_file.write(template)
        LOG.info("Compiled the templates for {0} and created the file {1}".format(chart['name'], filename))


def _extract_repo_name(img):
    indexes = [x[0] for x in enumerate(img) if x[1]=='/' or x[1]==':']
    index_of_the_first_slash = indexes[0] + 1
    index_of_the_tag_separator = indexes[-1]
    repository_name = img[ index_of_the_first_slash : index_of_the_tag_separator ]
    return repository_name


def _substitute_registry(images, replacement):
    images_lst = []
    for image_template in images:
        image_uri = str(image_template)
        for key,value in replacement.items():
            image_uri = image_uri.replace(key, value)
        images_lst.append(image_uri)
    return images_lst


"""
This module implements Update command
"""
import logging
from aws_deployment_manager.commands.base import Base
from aws_deployment_manager import utils
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class UpdateManager(Base):
    """ Main Class for Update Command """
    def __init__(self):
        Base.__init__(self)
        self.upload_templates()

    def pre_update(self):
        """
        Stack Pre Update Steps
        """
        LOG.info("Pre Update Started for stack {0}".format(self.infra_master_stack_name))

        LOG.info("Pre-Update Done")

    def update(self):
        """
        Stack Update Steps
        """
        LOG.info("Updating IDUN AWS for {0}".format(self.environment_name))

        # Invoke Cloudformation Stack Update
        response = self._update_idun_stack()

        utils.log_stack_details(response=response)
        LOG.info("SUCCESS - Updated IDUN AWS Stack")

    def post_update(self):
        """
        Stack Post Update Steps
        """
        LOG.info("Pre Update Started for {0}".format(self.infra_master_stack_name))

        LOG.info("Pre-Update Done")

    def _update_idun_stack(self):
        """
        Update AWS Cloudformation Stack
        :return: Stack Update Response
        """
        # Get URL for Master Template
        template_name = constants.TEMPLATE_INFRA_MASTER
        template_url = self.template_urls[template_name]

        # Prepare Template Parameters Object
        config_parameters = self.get_config_parameters_for_idun_cf_stack()

        LOG.info("Stack Name = {0}, Template = {1}".format(self.environment_name, template_url))
        response = self.aws_cfclient.update_stack(
            stack_name=self.environment_name,
            template_name=template_name,
            template_url=template_url,
            config_parameters=config_parameters
        )
        return response

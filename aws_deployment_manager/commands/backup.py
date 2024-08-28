"""
This module implements Backup Server Configure command
"""
import logging
from aws_deployment_manager.commands.base import Base
from aws_deployment_manager import constants

LOG = logging.getLogger(__name__)


class BackupManager(Base):
    """ Main Class for Configure command """
    def __init__(self):
        Base.__init__(self)
        self.cluster_name = ""
        self.outputs = {}
        self.load_stage_states(stage_log_path=constants.INSTALL_STAGE_LOG_PATH)

    def backup_configure(self):
        """
        IDUN Backup Server Configuration
        """
        LOG.info("Executing IDUN Backup Server Configuration Tasks...")
        security_groupid = self.aws_ec2client.create_securitygroup(group_name="Backup Securitygroup", vpc_id=self.vpcid)
        user_data = constants.USER_DATA.replace('PASS', self.config[constants.BACKUP_PASS])

        self.aws_ec2client.add_ingress_rule(security_group_id=security_groupid, from_port=22, to_port=22,
                                            ip_protocol= 'TCP', cidr_ip= '0.0.0.0/0')

        ec2_instance= self.aws_ec2client.create_ec2(disk_size=self.backup_disk, user_data=user_data,
                                                    image_id=self.backup_ami,
                                                    instance_type=self.backup_instance_type,
                                                    subnet_id=self.worker_node_subnet_01_id,
                                                    security_groupid=security_groupid,key_name=self.ssh_key_pair_name)
        LOG.info("IDUN Backup Server {} Created".format(ec2_instance))

    def update_ami(self, ami):
        """
        EIAP Backup Server Configuration
        """
        LOG.info("Executing EIAP Backup Server Configuration Tasks...")
        user_data = constants.USER_DATA.replace('PASS', self.config[constants.BACKUP_PASS])
        old_instance_id, volume_id, security_group_id = \
            self.aws_ec2client.get_instance_details_from_tag(constants.BACKUP_SERVER)
        snapshot_id = self.aws_ec2client.create_ebs_snapshot(volume_id)

        ec2_instance = self.aws_ec2client.create_ec2(disk_size=self.backup_disk, user_data=user_data, image_id=ami,
                                                     instance_type=self.backup_instance_type,
                                                     subnet_id=self.worker_node_subnet_01_id,
                                                     security_groupid=security_group_id,
                                                     key_name=self.ssh_key_pair_name, snapshot_id=snapshot_id)
        new_instance_id = ec2_instance[0].instance_id
        self.aws_ec2client.delete_ec2(old_instance_id)
        self.aws_ec2client.update_tag(old_instance_id, constants.NAME, constants.OLD_BACKUP_LABEL)
        self.aws_ec2client.update_tag(new_instance_id, constants.NAME, constants.BACKUP_SERVER)
        self.aws_ec2client.delete_volume(volume_id)
        self.aws_ec2client.delete_snapshot(snapshot_id)
        LOG.info("Backup Server AMI updated")


# pylint: skip-file
{
    'EnvironmentName': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'AWSRegion': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'K8SVersion': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'VPCID': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'ControlPlaneSubnetIds': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'WorkerNodeSubnetIds': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'SecondaryVpcCIDR': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'NodeInstanceType': {
        'required': True,
        'type': 'string'
    },
    'BackupInstanceType': {
        'required': True,
        'type': 'string'
    },
    'BackupAmiId': {
        'required': True,
        'type': 'string'
    },
    'BackupDisk': {
        'required': True,
        'type': 'number',
        'min': 20,
        'max': 200
    },
    'BackupPass': {
        'required': True,
         'type': 'string',
    },
    'DiskSize': {
        'required': True,
        'type': 'number',
        'min': 20,
        'max': 200
    },
    'MinNodes': {
        'required': True,
        'type': 'number',
        'min': 1,
        'max': 10
    },
    'MaxNodes': {
        'required': True,
        'type': 'number',
        'min': 1,
        'max': 50
    },
    'SshKeyPairName': {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'PrivateDomainName' : {
        'required': True,
        'type': 'string',
        'regex': '^\S*$'
    },
    'Hostnames': {
        'type': 'dict',
        'required': True,
        'valuesrules': {
            'type': 'string',
            'regex': '^\S*$'
        }
    },
    'KubeDownscaler': {
        'required': True,
        'type': 'boolean'
    },
    'DisablePublicAccess': {
        'required': True,
        'type': 'boolean'
    }
}
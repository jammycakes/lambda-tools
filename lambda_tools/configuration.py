"""
A set of classes and functions to parse the  `aws-lambda.yml` file and load in
the lambda configurations.
"""

import logging
import os.path
import boto3
import yaml
from . import util

log = logging.getLogger(__name__)

# ====== Loader class ====== #

class Loader(object):
    """
    This class loads in the lambda configuration. It provides some options to
    fetch the AWS account ID, resolve file paths, and create boto3 clients.

    It does not contain any logic.
    """

    def __init__(self, file, account_id=None, session=None):
        self.file = os.path.abspath(os.path.expanduser(file))
        self.folder = os.path.dirname(self.file)
        self.session = session
        self.account_id = account_id
        self._clients = {}

    def client(self, service_name, region_name=None):
        if not region_name in self._clients:
            self._clients[region_name] = {}
        region = self._clients[region_name]
        if service_name in region:
            return region[service_name]
        else:
            service = (self.session or boto3).client(service_name, region_name=region_name)
            region[service_name] = service
            return service

    def abspath(self, path):
        """
        Gets the absolute path from a path relative to the loader.
        """
        return os.path.join(self.folder, path)

    def get_data(self):
        with open(self.file) as f:
            return yaml.load(f)

    def get_configurations(self, data, functions):
        keys = set(data)
        if functions:
            keys = keys.intersection(functions)
        return (Lambda(self, key, **data[key]) for key in keys)

    def load(self, functions):
        self.account_id = int(self.account_id or self.client('sts').get_caller_identity().get('Account'))
        data = self.get_data()
        return self.get_configurations(data, functions)



# ====== Lambda class ====== #

class Lambda(object):
    """
    Encapsulates a lambda function, to be uploaded to AWS
    """

    def __init__(self, loader, name, source, handler, role,
        region=None,
        runtime='python3.6',
        description='',
        timeout=3,
        memory=None,
        vpc=None,
        subnets=None,
        security_groups=None,
        dead_letter=None,
        environment=None,
        kms_key=None,
        tracing=None,
        tags=None,
        requirements=None,
        package=None,
        # New parameters
        vpc_config=None,
        tracing_config=None,
        dead_letter_config=None,
        memory_size=128
    ):
        def warn(setting, should_use):
            log.warn('Setting: "{0}" is deprecated: use "{1}" instead.'.format(setting, should_use))
            log.warn('This setting will be removed in a future version of lambda_tools.')

        self.loader = loader
        self.name = name
        self.source = self.loader.abspath(source)
        self.role = role
        self.handler = handler
        self.region = region
        self.runtime = runtime
        self.description = description
        self.timeout = timeout

        if memory:
            warn("memory", "memory_size")
            self.memory = memory
        else:
            self.memory = memory_size

        if subnets:
            warn("subnets", "vpc_config:subnets")
            self.subnets = subnets
        if security_groups:
            warn("security_groups", "vpc_config:security_groups")
            self.security_groups = security_groups
        if vpc:
            warn("vpc", "vpc_config:name")
            self.vpc = vpc
        if vpc_config:
            self.subnets = [
                value['name'] if isinstance(value, dict) else value
                for value in vpc_config['subnets']
            ]
            self.security_groups = [
                value['name'] if isinstance(value, dict) else value
                for value in vpc_config['security_groups']
            ]
            self.vpc = vpc_config.get('name')

        if dead_letter:
            warn("dead_letter", "dead_letter_config:target_arn")
            self.dead_letter = dead_letter
        elif dead_letter_config:
            self.dead_letter = dead_letter_config.get('target_arn')

        self.environment = environment
        if isinstance(environment, dict):
            if len(environment) == 1 and 'variables' in environment:
                self.environment = environment['variables']
            else:
                warn("environment", "environment:variables")

        self.kms_key = kms_key.get('name') if isinstance(kms_key, dict) else kms_key

        if tracing:
            warn("tracing", "tracing_config:mode")
            self.tracing = tracing
        elif tracing_config:
            self.tracing = tracing_config['mode']

        self.tags = tags
        self.requirements = self.loader.abspath(requirements) if requirements else None
        self.package = self.loader.abspath(package) if package else self.source + '.zip'

        # Post-processing: use environment variables when appropriate
        if self.environment:
            util.assert_dict(self.environment, 'environment')
            for k in self.environment:
                if self.environment[k] == None:
                    self.environment[k] = os.environ.get(k, '')
        if self.tags:
            util.assert_dict(self.tags, 'tags')

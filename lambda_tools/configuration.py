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

class Loader(util.Serviceable):
    """
    This class loads in the lambda configuration. It provides some options to
    fetch the AWS account ID, resolve file paths, and create boto3 clients.

    It does not contain any logic.
    """

    def __init__(self, file):
        self.file = os.path.abspath(os.path.expanduser(file))
        self.folder = os.path.dirname(self.file)
        self.session = self.services.get(boto3.Session)
        self._clients = {}

    def client(self, service_name, region_name=None):
        if not region_name in self._clients:
            self._clients[region_name] = {}
        region = self._clients[region_name]
        if service_name in region:
            return region[service_name]
        else:
            service = self.session.client(service_name, region_name=region_name)
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
        return (Function(self, key, **data[key]) for key in keys)

    def load(self, functions):
        data = self.get_data()
        return self.get_configurations(data, functions)


# ====== Function class ====== #

class Function(util.Serviceable):
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
        memory_size=128,
        use_docker=False
    ):
        def warn(setting, should_use):
            log.warn('Setting: "{0}" is deprecated: use "{1}" instead.'.format(setting, should_use))
            log.warn('This setting will be removed in a future version of lambda_tools.')

        self.name = name
        self.source = loader.abspath(source)
        self.role = role
        self.handler = handler
        self.region = region
        self.runtime = runtime
        self.description = description
        self.timeout = timeout

        if memory:
            warn("memory", "memory_size")
            self.memory_size = memory
        else:
            self.memory_size = memory_size

        self.vpc_config = None
        if subnets:
            warn("subnets", "vpc_config:subnets")
            self.vpc_config = {
                "subnets": [ {'name': subnet } for subnet in subnets ]
            }
        if security_groups:
            warn("security_groups", "vpc_config:security_groups")
            self.vpc_config = self.vpc_config or {}
            self.vpc_config['security_groups'] = [
                { 'name': sg } for sg in security_groups
            ]
        if vpc:
            warn("vpc", "vpc_config:name")
            self.vpc_config = self.vpc_config or {}
            self.vpc_config['name'] = vpc

        if vpc_config:
            self.vpc_config = vpc_config
            self.vpc_config['subnets'] = [
                a if isinstance(a, dict) else { 'name': a }
                for a in self.vpc_config['subnets']
            ]
            self.vpc_config['security_groups'] = [
                a if isinstance(a, dict) else { 'name': a }
                for a in self.vpc_config['security_groups']
            ]

        if dead_letter:
            warn("dead_letter", "dead_letter_config:target_arn")
            self.dead_letter_config = {
                'target_arn': dead_letter
            }
        elif dead_letter_config:
            self.dead_letter_config = dead_letter_config
        else:
            self.dead_letter_config = None

        self.environment = environment
        if isinstance(environment, dict):
            if len(environment) == 1 and 'variables' in environment:
                self.environment = environment
            else:
                self.environment = {
                    'variables': environment
                }
                warn("environment", "environment:variables")

        self.kms_key = kms_key if isinstance(kms_key, dict) else { 'name': kms_key }

        if tracing:
            warn("tracing", "tracing_config:mode")
            self.tracing_config = {
                'mode': tracing
            }
        elif tracing_config:
            self.tracing_config = tracing_config
        else:
            self.tracing_config = None

        self.tags = tags
        self.requirements = loader.abspath(requirements) if requirements else None
        self.package = loader.abspath(package) if package else self.source + '.zip'
        self.use_docker = use_docker

        # use environment variables when appropriate
        if self.environment:
            util.assert_dict(self.environment, 'environment')
            for k in self.environment:
                if self.environment[k] == None:
                    self.environment[k] = os.environ.get(k, '')
        if self.tags:
            util.assert_dict(self.tags, 'tags')

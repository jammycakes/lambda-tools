"""
A set of classes and functions to parse the  `aws-lambda.yml` file and load in
the lambda configurations.
"""

import os.path
import boto3
import yaml
from . import util

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

    def load(self, functions):
        self.account_id = int(self.account_id or self.client('sts').get_caller_identity().get('Account'))
        with open(self.file) as f:
            cfg = yaml.load(f)

        keys = set(cfg)
        if functions:
            keys = keys.intersection(functions)
        return (Lambda(self, key, **cfg[key]) for key in keys)


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
        memory=128,
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
        use_docker=False
    ):
        self.loader = loader
        self.name = name
        self.source = self.loader.abspath(source)
        self.role = role
        self.handler = handler
        self.region = region
        self.runtime = runtime
        self.description = description
        self.timeout = timeout
        self.memory = memory
        self.subnets = subnets
        self.vpc = vpc
        self.security_groups = security_groups
        self.dead_letter = dead_letter
        self.environment = environment
        self.kms_key = kms_key
        self.tracing = tracing
        self.tags = tags
        self.requirements = self.loader.abspath(requirements) if requirements else None
        self.package = self.loader.abspath(package) if package else self.source + '.zip'
        self.use_docker = use_docker

        # Post-processing: use environment variables when appropriate
        if self.environment:
            util.assert_dict(self.environment, 'environment')
            for k in self.environment:
                if self.environment[k] == None:
                    self.environment[k] = os.environ.get(k, '')
        if self.tags:
            util.assert_dict(self.tags, 'tags')

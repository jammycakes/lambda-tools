"""
A set of classes and functions to parse the  `aws-lambda.yml` file and load in
the lambda configurations.
"""

import os.path

from . import mapper

class DeadLetterTargetConfig:
    sns = mapper.StringField()
    sqs = mapper.StringField()

    def validate(self):
        if bool(self.sns) == bool(self.sqs):
            return 'You must specify either sns or sqs, but not both.'


class DeadLetterConfig:
    target = mapper.ClassField(DeadLetterTargetConfig)
    target_arn = mapper.StringField()

    def validate(self):
        if bool(self.target) == bool(self.target_arn):
            return 'You must specify either target or target_arn, but not both.'


class EnvironmentConfig:
    variables = mapper.DictField(mapper.StringField(nullable=True), required=True)


class KmsKeyConfig:
    name = mapper.StringField()
    arn = mapper.StringField()

    def validate(self):
        if bool(self.name) == bool(self.arn):
            return 'You must specify either name or arn, but not both.'


class TracingConfig:
    mode = mapper.ChoiceField(choices=['PassThrough', 'Active'], required=True)

class NameOrIdConfig:
    id = mapper.StringField()
    name = mapper.StringField()

    def validate(self):
        if bool(self.id) == bool(self.name):
            return 'You must specify eother id or name, but not both.'


class VpcConfig:
    name = mapper.StringField()
    subnets = mapper.ListField(
        mapper.ClassField(NameOrIdConfig, default_field='name'),
        required=True
    )
    security_groups = mapper.ListField(
        mapper.ClassField(NameOrIdConfig, default_field='name'),
        required=True
    )


class RequirementConfig:
    file = mapper.StringField()

    def resolve(self, root):
        self.file = os.path.join(root, self.file)


class BuildConfig:
    source = mapper.StringField(required=True)
    requirements = mapper.ListField(mapper.ClassField(RequirementConfig))
    use_docker = mapper.BoolField(default=False)
    compile_dependencies = mapper.BoolField(default=False)
    package = mapper.StringField()

    def resolve(self, root):
        self.source = os.path.join(root, self.source)
        if self.package:
            self.package = os.path.join(root, self.package)
        else:
            self.package = self.source
            if self.package.endswith(os.sep) or self.package.endswith(os.altsep):
                self.package = self.package[:-1]
            self.package += '.zip'
        for requirement in self.requirements:
            requirement.resolve(root)


class DeployConfig:
    handler = mapper.StringField(required=True)
    role = mapper.StringField(required=True)

    description = mapper.StringField(default='')
    memory_size = mapper.IntField(default=128)
    region = mapper.StringField()
    timeout = mapper.IntField(default=3)

    dead_letter_config = mapper.ClassField(DeadLetterConfig)
    environment = mapper.ClassField(EnvironmentConfig)
    kms_key = mapper.ClassField(KmsKeyConfig)
    tags = mapper.DictField(mapper.StringField(nullable=True))
    tracing_config = mapper.ClassField(TracingConfig)
    vpc_config = mapper.ClassField(VpcConfig)


class FunctionConfig:
    runtime = mapper.ChoiceField(
        choices=[
            'nodejs',
            'nodejs4.3',
            'nodejs6.10',
            'java8',
            'python2.7',
            'python3.6',
            'dotnetcore1.0',
            'nodejs4.3-edge'
        ],
        default='python3.6'
    )
    build = mapper.ClassField(BuildConfig, required=True)
    deploy = mapper.ClassField(DeployConfig)


class GlobalConfig:
    version = mapper.IntField(required=True)
    functions = mapper.DictField(mapper.ClassField(FunctionConfig), required=True)


def upgrade_0_to_1(data):

    def copy_fields(func, *fields, **renamed_fields):
        result = {}
        for field in fields:
            if field in func:
                result[field] = func[field]

        for target in renamed_fields:
            source = renamed_fields[target]
            if source in func:
                result[target] = func[source]
            else:
                print(source + ' not found')

        return result

    def get_build_block(func):
        result = copy_fields(func,
            'source', 'compile_dependencies', 'package', 'use_docker'
        )
        if 'requirements' in func:
            result['requirements'] = [
                { 'file': func['requirements'] }
            ]
        return result

    def get_deploy_block(func):
        result = copy_fields(func,
            'handler', 'role',
            'description', 'region', 'tags', 'timeout',
            memory_size='memory'
        )
        if 'dead_letter' in func:
            result['dead_letter_config'] = {
                'target_arn': func['dead_letter']
            }
        if 'environment' in func:
            result['environment'] = {
                'variables': func['environment']
            }
        if 'kms_key' in func:
            result['kms_key'] = {
                'name': func['kms_key']
            }
        if 'security_groups' in func:
            result['vpc_config'] = {
                'security_groups': func['security_groups']
            }
        if 'subnets' in func:
            if not 'vpc_config' in result:
                result['vpc_config'] = {}
            result['vpc_config']['subnets'] = func['subnets']
        if 'tracing' in func:
            result['tracing_config'] = {
                'mode': func['tracing']
            }
        if 'vpc' in func:
            if not 'vpc_config' in result:
                result['vpc_config'] = {}
            result['vpc_config']['name'] = func['vpc']

        return result

    def transform_function(func):
        result = {
            'build': get_build_block(func),
            'deploy': get_deploy_block(func)
        }
        if 'runtime' in func:
            result['runtime'] = func['runtime']
        return result

    if isinstance(data.get('version'), int):
        return data

    return {
        'version': 1,
        'functions': dict([(f, transform_function(data[f])) for f in data])
    }


def upgrade(data):
    upgraded = upgrade_0_to_1(data)
    return upgraded

def load(filename):
    with open(filename) as f:
        data = yaml.load(f)
        data = upgrade(data)
        return mapper.parse(GlobalConfig, data)

# ====== VERSION 0.0.x STUFF ====== #

# To be replaced once the FunctionConfig-based settings are up and running.

import logging
import os.path
import boto3
import factoryfactory
import yaml

from . import util

log = logging.getLogger(__name__)


# ====== Loader class ====== #

class Loader(factoryfactory.Serviceable):
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

class Function(factoryfactory.Serviceable):
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
        use_docker=False,
        compile_dependencies=False
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
        self.compile_dependencies = compile_dependencies

        # use environment variables when appropriate
        if self.environment:
            util.assert_dict(self.environment, 'environment')
            for k in self.environment:
                if self.environment[k] == None:
                    self.environment[k] = os.environ.get(k, '')
        if self.tags:
            util.assert_dict(self.tags, 'tags')

"""
A set of classes and functions to parse the  `aws-lambda.yml` file and load in
the lambda configurations.
"""

import os
import os.path

import boto3
import yaml

from . import mapper

class DeadLetterTargetConfig:
    sns = mapper.StringField()
    sqs = mapper.StringField()

    def validate(self):
        if bool(self.sns) == bool(self.sqs):
            return 'You must specify either sns or sqs, but not both.'

    def get_arn(self, account_id, region):
        return 'arn:aws:' + ('sns:' if self.sns else 'sqs:') + \
            region + ':' + str(account_id) + ':' + str(self.sns or self.sqs)


class DeadLetterConfig:
    target = mapper.ClassField(DeadLetterTargetConfig)
    target_arn = mapper.StringField()

    def validate(self):
        if bool(self.target) == bool(self.target_arn):
            return 'You must specify either target or target_arn, but not both.'

    def resolve(self, account_id, region):
        if self.target:
            self.target_arn = self.target.get_arn(account_id, region)


class EnvironmentConfig:
    variables = mapper.DictField(mapper.StringField(nullable=True), required=True)

    def resolve(self, environment):
        for key in self.variables:
            if self.variables[key] == None:
                self.variables[key] = environment.get(key, '')

class KmsKeyConfig:
    name = mapper.StringField()
    arn = mapper.StringField()

    def validate(self):
        if bool(self.name) == bool(self.arn):
            return 'You must specify either name or arn, but not both.'

    def resolve(self, kms):
        if self.name:
            self.arn = kms.describe_key(KeyId='alias/' + self.name)['KeyMetadata']['Arn']


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

    def resolve(self, ec2):
        # First get the VPC ID
        if self.name:
            vpcs = ec2.describe_vpcs(Filters=[{
                'Name': 'tag:Name',
                'Values': [self.name]
            }])
            vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs']]
        else:
            vpc_ids = None

        # Next get the subnets and SGs that are specified by name
        subnets = dict([(s.name, s) for s in self.subnets if s.name])
        sgroups = dict([(s.name, s) for s in self.security_groups if s.name])

        # Next get the filter.
        filter = [{
            'Name': 'tag:Name',
            'Values': list(subnets)
        }]
        if vpc_ids:
            filter.append({
                'Name': 'vpc-id',
                'Values': vpc_ids
            })

        # Query EC2.
        subnet_data = ec2.describe_subnets(Filters=filter)['Subnets']
        filter[0]['Name'] = 'group-name'
        filter[0]['Values'] = list(sgroups)
        sgroup_data = ec2.describe_security_groups(Filters=filter)['SecurityGroups']

        # Construct name -> id mappings
        subnet_map = dict([
            (
                [tag['Value'] for tag in subnet['Tags'] if tag['Key'] == 'Name' ][0],
                subnet['SubnetId']
            )
            for subnet in subnet_data
        ])

        sgroup_map = dict([
            (sgroup['GroupName'], sgroup['GroupId'])
            for sgroup in sgroup_data
        ])

        # Set IDs
        for subnet in subnets.values():
            subnet.id = subnet_map.get(subnet.name)
        for sgroup in sgroups.values():
            sgroup.id = sgroup_map.get(sgroup.name)


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

    def resolve(self, services):
        """
        Resolves IDs and ARNs for resources that are specified by name.

        @param services:
            The factoryfactory.ServiceLocator instance used to locate things.
        """
        session = services.get(boto3.Session, region_name=self.region)
        self.region = self.region or session.region_name
        self.account_id = session.client('sts').get_caller_identity().get('Account')
        if self.dead_letter_config:
            self.dead_letter_config.resolve(self.account_id, self.region)
        if self.kms_key:
            self.kms_key.resolve(session.client('kms'))
        if self.vpc_config:
            self.vpc_config.resolve(session.client('ec2'))
        # Forces the role name into ARN format.
        if not self.role.startswith('arn:aws:iam'):
            self.role = 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.role)
        # Passthrough of environment variables
        if self.environment:
            self.environment.resolve(services.get(os.environ))


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

    x = __builtins__

class Configuration:
    version = mapper.IntField(required=True)
    functions = mapper.DictField(mapper.ClassField(FunctionConfig), required=True)
    root = ''

    def get_functions(self, names):
        if not names:
            return self.functions
        nonexistent = set(names).difference(self.functions)
        if nonexistent:
            raise ValueError(
                'Undefined functions: ' + ', '.join(nonexistent)
            )
        return dict([
            (name, self.functions[name])
            for name in names
        ])


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
        config = mapper.parse(Configuration, data)
        config.root = os.path.dirname(filename)
        return config

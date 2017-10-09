"""
Functionality to instantiate and upload the lambda in AWS.
"""

import boto3
import os
import os.path
import yaml

class LambdaError(Exception):
    pass

def _assert_dict(data, name):
    if isinstance(data, dict):
        return data
    else:
        raise LambdaError(name + ' needs to be a dictionary')


def _normpath(path, rootpath=None):
    if path.startswith('~'):
        return os.path.expanduser(path)
    elif rootpath:
        return os.path.join(rootpath, path)
    else:
        path = os.path.abspath(path)

class Lambda(object):
    """
    Encapsulates a lambda function, to be uploaded to AWS
    """

    def __init__(self, name, account_id, curdir, source, handler, role,
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
        package=None
    ):
        self.name = name
        self.account_id = account_id
        self.source = _normpath(source, curdir)
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
        self.requirements = _normpath(requirements, curdir) if requirements else None
        self.package = _normpath(package, curdir) if package else self.source + '.zip'

        self.built = False

        self._session = boto3.session.Session(region_name=self.region)

        # Post-processing: use environment variables when appropriate
        if self.environment:
            _assert_dict(self.environment, 'environment')
            for k in self.environment:
                if self.environment[k] == None:
                    self.environment[k] = os.environ.get(k, '')
        if self.tags:
            _assert_dict(self.tags, 'tags')


    def _get_aws_client(self, name):
        return self._session.client(name)


    def _get_role_arn(self):
        """
        Forces the role name into ARN format.
        """
        if self.role.startswith('arn:aws:iam'):
            return self.role
        else:
            return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.role)


    def _get_vpcs(self):
        if not self.vpc:
            return None
        elif not hasattr(self, '_vpc_ids'):
            client = self._get_aws_client('ec2')
            vpcs = client.describe_vpcs(Filters=[{
                'Name': 'tag:Name',
                'Values': [ self.vpc ]
            }])
            self._vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs']]

        return self._vpc_ids


    def _get_subnets(self):
        if not hasattr(self, '_subnet_ids'):
            client = self._get_aws_client('ec2')
            filters = [{
                'Name': 'tag:Name',
                'Values': self.subnets
            }]
            if self.vpc:
                filters.append({
                    'Name': 'vpc-id',
                    'Values': self._get_vpcs()
                })

            subnets = client.describe_subnets(Filters=filters)
            self._subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]

        return self._subnet_ids


    def _get_security_groups(self):
        if not hasattr(self, '_security_group_ids'):
            client = self._get_aws_client('ec2')
            filters = [{
                'Name': 'group-name',
                'Values': self.security_groups
            }]
            if self.vpc:
                filters.append({
                    'Name': 'vpc-id',
                    'Values': self._get_vpcs()
                })
            groups = client.describe_security_groups(Filters=filters)
            self._security_group_ids = [group['GroupId'] for group in groups['SecurityGroups']]
        return self._security_group_ids


    def _get_kms_key_arn(self):
        # get KMS key ARN by alias
        if not hasattr(self, '_kms_key_arn'):
            client = self._get_aws_client('kms')
            key = client.describe_key(KeyId='alias/' + self.kms_key)
            self._kms_key_arn = key['KeyMetadata']['Arn']
        return self._kms_key_arn


    def _get_code(self):
        if not self.built:
            raise LambdaError('The lambda has not yet been built.')
        with open(self.package, 'rb') as data:
            return data.read()


    # ====== Get function configuration data ====== #

    def _get_function_configuration_data(self):
        result = {
            'FunctionName': self.name,
            'Runtime': self.runtime,
            'Role': self._get_role_arn(),
            'Handler': self.handler,
            'Description': self.description,
            'Timeout': self.timeout,
            'MemorySize': self.memory
        }
        if self.subnets or self.security_groups:
            result['VpcConfig'] = {
                'SubnetIds': self._get_subnets(),
                'SecurityGroupIds': self._get_security_groups()
            }
        if self.dead_letter:
            result['DeadLetterConfig'] = {
                'TargetArn': self.dead_letter
            }
        if self.environment:
            result['Environment'] = {
                'Variables': self.environment
            }
        if self.kms_key:
            result['KMSKeyArn'] = self._get_kms_key_arn()
        if self.tracing:
            result['TracingConfig'] = {
                'Mode': self.tracing
            }
        return result


    # ====== Get function creation data ====== #

    def _get_function_creation_data(self):
        result = self._get_function_configuration_data()
        result['Publish'] = True
        result['Code'] = {
            'ZipFile': self._get_code()
        }
        if self.tags:
            result['Tags'] = self.tags, 'tags'
        return result


    # ====== Get function code ====== #

    def _get_function_code(self):
        return {
            'FunctionName': self.name,
            'ZipFile': self._get_code(),
            'Publish': True
        }


    # ====== Build the package ====== #

    def build(self, silent=False):
        """
        Builds the package from source, saving it to the given location.
        """
        from .package import package
        package(self.source, self.requirements, self.package, silent=silent)
        self.built = True


    # ====== Create a function ====== #

    def create(self, silent=False):
        """
        Creates the lambda
        """
        if not self.built:
            self.build(silent=silent)
        data = self._get_function_creation_data()
        aws = self._get_aws_client('lambda')
        result = aws.create_function(**data)
        self.arn = result['FunctionArn']


    # ====== Update a function ====== #

    def update(self, silent=False):
        """
        Updates the lambda
        """
        if not self.built:
            self.build(silent=silent)
        aws = self._get_aws_client('lambda')

        # Update the configuration data
        data = self._get_function_configuration_data()
        result = aws.update_function_configuration(**data)
        self.arn = result['FunctionArn']

        # Update function code
        code = self._get_function_code()
        aws.update_function_code(**code)

        # Update the tags
        tags = aws.list_tags(Resource=self.arn)
        tags_to_clear = [x for x in tags['Tags'] if x not in self.tags]
        if tags_to_clear:
            aws.untag_resource(Resource=self.arn, TagKeys=tags_to_clear)
        if self.tags:
            aws.tag_resource(Resource=self.arn, Tags=self.tags)


    # ====== Deploy ====== #

    def deploy(self, silent=False):
        aws = self._get_aws_client('lambda')

        def exists():
            import botocore.exceptions
            try:
                aws.get_function_configuration(FunctionName=self.name)
                return True
            except botocore.exceptions.ClientError as ex:
                return False

        if exists():
            self.update(silent=silent)
        else:
            self.create(silent=silent)


def load(filename, functions=None, account_id=None):
    """
    Loads in the lambdas from the aws-lambda.yml file.

    @param filename
        Path to the aws-lambda.yml file.
    @param functions
        A list of all the lambda functions that have been requested.
    @account_id
        The AWS account ID.
    """
    if not account_id:
        account_id = boto3.client('sts').get_caller_identity().get('Account')
    if filename.startswith('~'):
        filename = os.path.expanduser(filename)
    else:
        filename = os.path.abspath(filename)
    dirname = os.path.dirname(filename)
    with open(filename) as f:
        cfg = yaml.load(f)

    keys = set(cfg)
    if functions:
        keys = keys.intersection(functions)
    return [Lambda(name, account_id, dirname, **cfg[name]) for name in keys]
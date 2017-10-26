"""
Functionality to instantiate and upload the lambda in AWS.
"""

from . import configuration
from . import package
from . import util

import boto3

class LambdaError(Exception):
    pass


def _lookup_ids(items, **lookups):
    """
    Given a list of item descriptors that may specify either their IDs or their
    names, returns their IDs.

    @param items:
        The items loaded in from the YAML file. Their YAML representation
        would look like this:
        ```
        items:
        - item_1_name
        - name: item_2_name
        - id: item_3_id
        ```

    @param lookups:
        A dictionary of functions that take a list of names, ARNs or whatever,
        and returns their IDs.
    """

    from collections import defaultdict
    dct = defaultdict(list)
    for item in items:
        if isinstance(item, dict):
            for k in item:
                dct[k].append(item[k])
    lookups[id] = lookups.get(id, lambda x: x)
    result = []
    for k in lookups:
        result.extend(lookups[k](dct[k]))
    return result


class Lambda(util.Serviceable):
    """
    Encapsulates a lambda function, to be uploaded to AWS
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.built = False
        self.arn = None
        self.account_id = self.services.get('aws-account-id')

    def _get_aws_client(self, service_name):
        return self.services.get(boto3.Session).client(service_name, self.cfg.region)

    def _get_role_arn(self):
        """
        Forces the role name into ARN format.
        """
        if self.cfg.role.startswith('arn:aws:iam'):
            return self.cfg.role
        else:
            return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.cfg.role)


    def _get_vpcs(self):

        def lookup_vpcs(names):
            client = self._get_aws_client('ec2')
            vpcs = client.describe_vpcs(Filters=[{
                'Name': 'tag:Name',
                'Values': names
            }])
            return [vpc['VpcId'] for vpc in vpcs['Vpcs']]

        if not self.cfg.vpc_config:
            return None
        elif not hasattr(self, '_vpc_ids'):
            self._vpc_ids = _lookup_ids([self.cfg.vpc_config], name=lookup_vpcs)

        return self._vpc_ids


    def _get_subnets(self):

        def lookup_subnets(names):
            vpcs = self._get_vpcs()
            client = self._get_aws_client('ec2')
            filters = [{
                'Name': 'tag:Name',
                'Values': names
            }]
            if vpcs:
                filters.append({
                    'Name': 'vpc-id',
                    'Values': vpcs
                })

            subnets = client.describe_subnets(Filters=filters)
            return [subnet['SubnetId'] for subnet in subnets['Subnets']]

        if not hasattr(self, '_subnet_ids'):
            subnets = self.cfg.vpc_config['subnets']
            self._subnet_ids = _lookup_ids(subnets, name=lookup_subnets)

        return self._subnet_ids


    def _get_security_groups(self):

        def lookup_groups(names):
            vpcs = self._get_vpcs()
            client = self._get_aws_client('ec2')
            filters = [{
                'Name': 'group-name',
                'Values': names
            }]
            if vpcs:
                filters.append({
                    'Name': 'vpc-id',
                    'Values': vpcs
                })

            groups = client.describe_security_groups(Filters=filters)
            return [group['GroupId'] for group in groups['SecurityGroups']]

        if not hasattr(self, '_security_group_ids'):
            groups = self.cfg.vpc_config['security_groups']
            self._security_group_ids = _lookup_ids(groups, name=lookup_groups)

        return self._security_group_ids


    def _get_kms_key_arn(self):
        # get KMS key ARN by alias
        if not hasattr(self, '_kms_key_arn'):
            client = self._get_aws_client('kms')
            self._kms_key_arn = self.cfg.kms_key.get('arn') or \
                client.describe_key(KeyId='alias/' + self.cfg.kms_key['name'])['KeyMetadata']['Arn']
        return self._kms_key_arn


    def _get_dead_letter_arn(self):

        def get_sns_arn(topic):
            return "arn:aws:sns:{0}:{1}:{2}".format(
                self.services.get(boto3.Session).region_name,
                self.account_id,
                topic
            )

        def get_sqs_arn(queue):
            return "arn:aws:sqs:{0}:{1}:{2}".format(
                self.services.get(boto3.Session).region_name,
                self.account_id,
                queue
            )

        if self.cfg.dead_letter_config:
            dcfg = self.cfg.dead_letter_config

            if 'target_arn' in dcfg:
                return dcfg['target_arn']
            elif 'target' in dcfg:
                if 'sns' in dcfg['target']:
                    return get_sns_arn(dcfg['target']['sns'])
                elif 'sqs' in dcfg['target']:
                    return get_sqs_arn(dcfg['target']['sqs'])
            return None

    def _get_code(self):
        if not self.built:
            raise LambdaError('The lambda has not yet been built.')
        with open(self.cfg.package, 'rb') as data:
            return data.read()


    # ====== Get function configuration data ====== #

    def _get_function_configuration_data(self):
        result = {
            'FunctionName': self.cfg.name,
            'Runtime': self.cfg.runtime,
            'Role': self._get_role_arn(),
            'Handler': self.cfg.handler,
            'Description': self.cfg.description,
            'Timeout': self.cfg.timeout,
            'MemorySize': self.cfg.memory_size
        }

        if self.cfg.vpc_config:
            result['VpcConfig'] = {
                'SubnetIds': self._get_subnets(),
                'SecurityGroupIds': self._get_security_groups()
            }
        if self.cfg.dead_letter_config:
            result['DeadLetterConfig'] = {
                'TargetArn': self._get_dead_letter_arn()
            }
        if self.cfg.environment:
            result['Environment'] = {
                'Variables': self.cfg.environment['variables']
            }
        if self.cfg.kms_key:
            result['KMSKeyArn'] = self._get_kms_key_arn()
        if self.cfg.tracing_config:
            result['TracingConfig'] = {
                'Mode': self.cfg.tracing_config['mode']
            }
        return result


    # ====== Get function creation data ====== #

    def _get_function_creation_data(self):
        result = self._get_function_configuration_data()
        result['Publish'] = True
        result['Code'] = {
            'ZipFile': self._get_code()
        }
        if self.cfg.tags:
            result['Tags'] = self.cfg.tags, 'tags'
        return result


    # ====== Get function code ====== #

    def _get_function_code(self):
        return {
            'FunctionName': self.cfg.name,
            'ZipFile': self._get_code(),
            'Publish': True
        }


    # ====== Build the package ====== #

    def build(self, silent=False):
        """
        Builds the package from source, saving it to the given location.
        """
        pkg = package.Package(self.cfg, use_docker=True, silent=silent)
        pkg.create()
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
        tags_to_clear = [x for x in tags['Tags'] if x not in self.cfg.tags]
        if tags_to_clear:
            aws.untag_resource(Resource=self.arn, TagKeys=tags_to_clear)
        if self.cfg.tags:
            aws.tag_resource(Resource=self.arn, Tags=self.cfg.tags)


    # ====== Deploy ====== #

    def deploy(self, silent=False):
        """
        Deploys the lambda to AWS.
        """
        aws = self._get_aws_client('lambda')

        def exists():
            """
            Tests to see if the lambda exists.
            """
            import botocore.exceptions
            try:
                aws.get_function_configuration(FunctionName=self.cfg.name)
                return True
            except botocore.exceptions.ClientError:
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
    services = util.ServiceLocator()
    services.register(configuration.Loader, configuration.Loader, singleton=True)
    services.register(
        'aws-account-id',
        lambda *a, **k: int(
            account_id or
            services.get(boto3.Session).client('sts').get_caller_identity().get('Account')
        ),
        singleton=True
    )
    loader = services.get(configuration.Loader, filename)
    return [services.get(Lambda, cfg) for cfg in loader.load(functions)]

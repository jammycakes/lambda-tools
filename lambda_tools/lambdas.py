"""
Functionality to instantiate and upload the lambda in AWS.
"""

from . import configuration
from . import package

class LambdaError(Exception):
    pass

class Lambda(object):
    """
    Encapsulates a lambda function, to be uploaded to AWS
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.built = False
        self.arn = None

    def _get_aws_client(self, service_name):
        return self.cfg.loader.client(service_name, self.cfg.region)

    def _get_role_arn(self):
        """
        Forces the role name into ARN format.
        """
        if self.cfg.role.startswith('arn:aws:iam'):
            return self.cfg.role
        else:
            return 'arn:aws:iam::{0}:role/{1}'.format(self.cfg.loader.account_id, self.cfg.role)


    def _get_vpcs(self):
        if not self.cfg.vpc:
            return None
        elif not hasattr(self, '_vpc_ids'):
            client = self._get_aws_client('ec2')
            vpcs = client.describe_vpcs(Filters=[{
                'Name': 'tag:Name',
                'Values': [ self.cfg.vpc ]
            }])
            self._vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs']]

        return self._vpc_ids


    def _get_subnets(self):
        if not hasattr(self, '_subnet_ids'):
            client = self._get_aws_client('ec2')
            filters = [{
                'Name': 'tag:Name',
                'Values': self.cfg.subnets
            }]
            if self.cfg.vpc:
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
                'Values': self.cfg.security_groups
            }]
            if self.cfg.vpc:
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
            key = client.describe_key(KeyId='alias/' + self.cfg.kms_key)
            self._kms_key_arn = key['KeyMetadata']['Arn']
        return self._kms_key_arn


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
            'MemorySize': self.cfg.memory
        }
        if self.cfg.subnets or self.cfg.security_groups:
            result['VpcConfig'] = {
                'SubnetIds': self._get_subnets(),
                'SecurityGroupIds': self._get_security_groups()
            }
        if self.cfg.dead_letter:
            result['DeadLetterConfig'] = {
                'TargetArn': self.cfg.dead_letter
            }
        if self.cfg.environment:
            result['Environment'] = {
                'Variables': self.cfg.environment
            }
        if self.cfg.kms_key:
            result['KMSKeyArn'] = self._get_kms_key_arn()
        if self.cfg.tracing:
            result['TracingConfig'] = {
                'Mode': self.cfg.tracing
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
        pkg = package.Package(self.cfg, silent=silent)
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
    loader = configuration.Loader(filename, account_id=account_id)
    return [Lambda(cfg) for cfg in loader.load(functions)]

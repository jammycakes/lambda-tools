"""
Functionality to instantiate and upload the lambda in AWS.
"""

import os.path

import boto3
import factoryfactory

from lambda_tools import configuration

class DeployError(Exception):
    pass

class Deployer(factoryfactory.Serviceable):

    def __init__(self, func, name):
        if not func.deploy:
            raise DeployError(name + ' is not configured for deployment to AWS.')

        self.func = func
        self.name = name
        self._session = self.services.get(boto3.Session)
        self.region = self.func.deploy.region or self._session.region_name

    def _get_aws_client(self, service_name):
        return self._session.client(service_name, self.region)

    def _get_code(self):
        with open(self.func.build.package, 'rb') as data:
            return data.read()


    # ====== Get function configuration data ====== #

    def _get_function_configuration_data(self):
        cfg = self.func
        deploy = cfg.deploy
        result = {
            'FunctionName': self.name,
            'Runtime': cfg.runtime,
            'Role': deploy.role,
            'Handler': deploy.handler,
            'Description': deploy.description,
            'Timeout': deploy.timeout,
            'MemorySize': deploy.memory_size
        }

        if deploy.vpc_config:
            result['VpcConfig'] = {
                'SubnetIds': [
                    subnet.id for subnet in deploy.vpc_config.subnets
                ],
                'SecurityGroupIds': [
                    sgroup.id for sgroup in deploy.vpc_config.security_groups
                ]
            }

        if deploy.dead_letter_config:
            result['DeadLetterConfig'] = {
                'TargetArn': deploy.dead_letter_config.target_arn
            }

        if deploy.environment:
            result['Environment'] = {
                'Variables': deploy.environment.variables
            }
        if deploy.kms_key:
            result['KMSKeyArn'] = deploy.kms_key.arn

        if deploy.tracing_config:
            result['TracingConfig'] = {
                'Mode': deploy.tracing_config.mode
            }
        return result


    # ====== Get function creation data ====== #

    def _get_function_creation_data(self):
        result = self._get_function_configuration_data()
        result['Publish'] = True
        result['Code'] = {
            'ZipFile': self._get_code()
        }
        if self.func.deploy.tags:
            result['Tags'] = self.func.deploy.tags, 'tags'
        return result


    # ====== Get function code ====== #

    def _get_function_code(self):
        return {
            'FunctionName': self.name,
            'ZipFile': self._get_code(),
            'Publish': True
        }


    # ====== Create a function ====== #

    def create(self):
        """
        Creates the lambda
        """
        data = self._get_function_creation_data()
        aws = self._get_aws_client('lambda')
        result = aws.create_function(**data)
        self.arn = result['FunctionArn']


    # ====== Update a function ====== #

    def update(self, silent=False):
        """
        Updates the lambda
        """
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
        tags_to_clear = [x for x in tags['Tags'] if x not in self.func.deploy.tags]
        if tags_to_clear:
            aws.untag_resource(Resource=self.arn, TagKeys=tags_to_clear)
        if self.func.deploy.tags:
            aws.tag_resource(Resource=self.arn, Tags=self.func.deploy.tags)


    # ====== Deploy ====== #

    def deploy(self):
        config = self.services.get(configuration.Configuration)
        self.func.build.resolve(config.root)
        if not os.path.isfile(self.func.build.package):
            raise DeployError(self.name + ' has not yet been built. Please run ltools build ' + self.name)
        self.func.deploy.resolve(self.services)
        aws = self._get_aws_client('lambda')

        def exists():
            """
            Tests to see if the lambda exists.
            """
            import botocore.exceptions
            try:
                aws.get_function_configuration(FunctionName=self.name)
                return True
            except botocore.exceptions.ClientError:
                return False

        if exists():
            self.update()
        else:
            self.create()


class DeployCommand(factoryfactory.Serviceable):

    def __init__(self, functions):
        self.functions = functions

    def run(self):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(self.functions)
        for name in functions:
            funcdef = functions[name]
            package = self.services.get(Deployer, funcdef, name)
            package.deploy()

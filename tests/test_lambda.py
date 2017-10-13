import os.path
import unittest

import mock_boto3
from lambda_tools import configuration
from lambda_tools import lambdas


class MockLoader(configuration.Loader):

    def __init__(self, file, account_id=None, session=None):
        super().__init__(file, mock_boto3.MOCK_ACCOUNT_ID, None)
        self.services = {
            "ec2": mock_boto3.MockEc2Client(),
            "kms": mock_boto3.MockKmsClient(),
            "lambda": mock_boto3.MockLambdaClient()
        }

    def client(self, service_name, region_name=None):
        return self.services[service_name]


class TestLambda(unittest.TestCase):

    def get_loader(self, filename):
        filename = os.path.abspath(os.path.join(__file__, '..', filename))
        return MockLoader(filename)

    def test_lambda_from_0_configuration(self):
        self.maxDiff = None
        loader = self.get_loader('aws-lambda.0.0-0.1.yml')
        cfg = loader.load(None)
        for item in cfg:
            l = lambdas.Lambda(item)
            actual = l._get_function_configuration_data()
            expected = {
                'FunctionName': item.name,
                'Runtime': 'python3.6',
                'Role': 'arn:aws:iam::{0}:role/service-role/NONTF-lambda'.format(mock_boto3.MOCK_ACCOUNT_ID),
                'Handler': 'hello.handler',
                'Description': 'A basic Hello World handler',
                'Timeout': 60,
                'MemorySize': 128,
                'VpcConfig': {
                    'SubnetIds': [ 'subnet-12345678', 'subnet-11111111' ],
                    'SecurityGroupIds': [ 'sg-12345678' ]
                },
                'DeadLetterConfig': {
                    'TargetArn': 'some-dead-letter-arn'
                },
                'Environment': {
                    'Variables': {
                        'foo': 'baz',
                        'bar': 'glarch'
                    }
                },
                'KMSKeyArn': 'arn:aws:kms:{0}:{1}:key/12345678-dead-beef-face-cafe12345678'.format(
                    mock_boto3.MOCK_AWS_REGION, mock_boto3.MOCK_ACCOUNT_ID
                ),
                "TracingConfig": {
                    "Mode": "PassThrough"
                }
            }
            self.assertDictEqual(expected, actual)

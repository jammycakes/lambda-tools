import os.path
import unittest
import yaml

import boto3
from lambda_tools import factoryfactory
from lambda_tools import configuration
from lambda_tools import mapper
import mock_boto3

def load_yaml(filename):
    testfile = os.path.join(os.path.dirname(__file__), filename)
    with open(testfile) as f:
        return yaml.safe_load(f)

class TestSchema(unittest.TestCase):

    def setUp(self):
        self.data = load_yaml('aws-lambda-1.yml')
        self.config = mapper.parse(configuration.Configuration, self.data)
        self.func = self.config.functions['test-0.1']

    def test_version(self):
        self.assertEqual(1, self.config.version)

    def test_functions(self):
        self.assertEqual(1, len(self.config.functions))

    def test_runtime(self):
        self.assertEqual(self.func.runtime, 'python3.6')


    def test_build(self):
        build = self.func.build
        self.assertEqual('src/hello_world', build.source)
        self.assertEqual('requirements.txt', build.requirements[0].file)
        self.assertEqual(1, len(build.requirements))
        self.assertFalse(build.use_docker)
        self.assertFalse(build.compile_dependencies)
        self.assertEqual('build/hello_world.zip', build.package)

    def test_deploy_basics(self):
        deploy = self.func.deploy
        self.assertEqual(deploy.description, 'A basic Hello World handler')
        self.assertEqual(deploy.region, 'eu-west-1')
        self.assertEqual(deploy.handler, 'hello.handler')
        self.assertEqual(deploy.memory_size, 128)
        self.assertEqual(deploy.timeout, 60)
        self.assertEqual(deploy.role, 'service-role/NONTF-lambda')

    def test_deploy_vpc_config(self):
        vpc = self.func.deploy.vpc_config
        self.assertEqual(vpc.name, 'My VPC')
        subnets = sorted([s.name for s in vpc.subnets])
        self.assertListEqual(
            sorted(['Public subnet', 'Private subnet']),
            subnets
        )
        security_groups = sorted([s.name for s in vpc.security_groups])
        self.assertListEqual(['allow_database'], security_groups)

    def test_deploy_kms_key(self):
        self.assertEqual('aws/lambda', self.func.deploy.kms_key.name)

    def test_deploy_tags(self):
        self.assertDictEqual({'wibble': 'wobble'}, self.func.deploy.tags)

    def test_deploy_environment_variables(self):
        self.assertDictEqual(
            { 'foo': 'baz', 'bar': None },
            self.func.deploy.environment.variables
        )

    def test_deploy_tracing_config(self):
        self.assertEqual('PassThrough', self.func.deploy.tracing_config.mode)

    def test_deploy_dead_letter_config(self):
        self.assertEqual('some-dead-letter-arn', self.func.deploy.dead_letter_config.target_arn)


class TestBuildResolve(unittest.TestCase):

    def setUp(self):
        self.data = load_yaml('aws-lambda-1.yml')
        self.config = mapper.parse(configuration.Configuration, self.data)
        self.func = self.config.functions['test-0.1']
        self.func.build.resolve('/home/test')

    def test_source_path(self):
        self.assertEqual('/home/test/src/hello_world', self.func.build.source)

    def test_requirements_path(self):
        self.assertEqual('/home/test/requirements.txt', self.func.build.requirements[0].file)

    def test_package_path(self):
        self.assertEqual('/home/test/build/hello_world.zip', self.func.build.package)


class TestDeployResolve(unittest.TestCase):

    def get_resolved(self, data):
        data2 = data.copy()
        data2['handler'] = 'hello.handler'
        data2['role'] = 'service-role/NONTF-lambda'
        services = factoryfactory.ServiceLocator()
        services.register(boto3.Session, mock_boto3.MockSession)
        deploy = mapper.parse(configuration.DeployConfig, data2)
        deploy.resolve(services)
        return deploy

    def test_resolve_region(self):
        deploy = self.get_resolved({})
        self.assertEqual('eu-west-1', deploy.region)

    def test_resolve_dead_letter_config(self):
        deploy = self.get_resolved({
            'dead_letter_config': {
                'target': {
                    'sns': 'some-sns-id'
                }
            }
        })
        self.assertEqual(
            'arn:aws:sns:eu-west-1:123456789012:some-sns-id',
            deploy.dead_letter_config.target_arn
        )

    def test_resolve_kms_key(self):
        deploy = self.get_resolved({
            'kms_key': {
                'name': 'aws/lambda'
            }
        })
        self.assertEqual(
            'arn:aws:kms:eu-west-1:123456789012:key/12345678-dead-beef-face-cafe12345678',
            deploy.kms_key.arn
        )

    def test_resolve_vpc_config_subnets(self):
        deploy = self.get_resolved({
            'vpc_config': {
                'subnets': [
                    {'name': 'Public subnet'},
                    {'name': 'Private subnet'}
                ],
                'security_groups': [
                    {'name': 'allow_database'}
                ]
            }
        })
        self.assertListEqual(
            ['subnet-12345678', 'subnet-11111111'],
            [x.id for x in deploy.vpc_config.subnets]
        )

    def test_resolve_vpc_config_security_groups(self):
        deploy = self.get_resolved({
            'vpc_config': {
                'subnets': [
                    {'name': 'Public subnet'},
                    {'name': 'Private subnet'}
                ],
                'security_groups': [
                    {'name': 'allow_database'}
                ]
            }
        })
        self.assertListEqual(
            ['sg-12345678'],
            [x.id for x in deploy.vpc_config.security_groups]
        )

    def test_resolve_vpc_config_with_specified_vpc(self):
        deploy = self.get_resolved({
            'vpc_config': {
                'name': 'vpc-12345678',
                'subnets': [
                    {'name': 'Public subnet'},
                    {'name': 'Private subnet'}
                ],
                'security_groups': [
                    {'name': 'allow_database'}
                ]
            }
        })
        self.assertListEqual(
            ['sg-12345678'],
            [x.id for x in deploy.vpc_config.security_groups]
        )
        self.assertListEqual(
            ['subnet-12345678', 'subnet-11111111'],
            [x.id for x in deploy.vpc_config.subnets]
        )



class TestUpgrade(TestSchema):

    def setUp(self):
        self.data = load_yaml('aws-lambda-0.yml')
        self.data = configuration.upgrade(self.data)
        self.config = mapper.parse(configuration.Configuration, self.data)
        self.func = self.config.functions['test-0.0']

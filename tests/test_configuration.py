import os.path
import unittest
import yaml
from lambda_tools import configuration
from lambda_tools import mapper

class TestSchema(unittest.TestCase):

    def setUp(self):
        testfile = os.path.join(os.path.dirname(__file__), 'aws-lambda-1.yml')
        with open(testfile) as f:
            self.data = yaml.load(f)
        self.config = mapper.parse(configuration.GlobalConfig, self.data)
        self.func = self.config.functions['test-0.1']

    def test_version(self):
        self.assertEqual(1, self.config.version)

    def test_functions(self):
        self.assertEqual(1, len(self.config.functions))
        self.assertIn('test-0.1', self.config.functions)

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
        self.assertEqual(deploy.runtime, 'python3.6')
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
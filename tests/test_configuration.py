import os.path
import unittest
import yaml

import mock_boto3
from lambda_tools import configuration


class MockLoader(configuration.Loader):

    def __init__(self, file, account_id=None, session=None):
        super.__init__(self, file, 1234567890, None)


class TestConfigurations(unittest.TestCase):

    def get_loader(self, filename):
        filename = os.path.abspath(os.path.join(__file__, '..', filename))
        return configuration.Loader(filename, account_id=1234567890)

    def test_bad_configurations(self):
        loader = self.get_loader('aws-lambda.bad.yml')
        data = loader.get_data()
        for c in data:
            try:
                l = configuration.Function(loader, c, **data[c])
                self.fail('Configuration ' + l.name + ' failed to fail')
            except TypeError:
                pass

    def test_0_to_1_migration(self):
        loader = self.get_loader('aws-lambda.0.0-0.1.yml')
        data = list(loader.load(False))
        dict0 = vars(data[0])
        dict1 = vars(data[1])

        for k in dict0:
            if isinstance(dict0[k], dict):
                self.assertDictEqual(dict0[k], dict1[k])
            elif isinstance(dict0[k], str):
                self.assertEqual(
                    dict0[k],
                    dict1[k].replace(data[1].name, data[0].name)
                )
            elif isinstance(dict0[k], list):
                self.assertListEqual(dict0[k], dict1[k])
            else:
                self.assertEqual(dict0[k], dict1[k])

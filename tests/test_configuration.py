import os.path
import unittest
import yaml

from lambda_tools import configuration

class TestConfigurations(unittest.TestCase):

    def get_loader(self, filename):
        filename = os.path.abspath(os.path.join(__file__, '..', filename))
        return configuration.Loader(filename, account_id=1234567890)

    def test_bad_configurations(self):
        loader = self.get_loader('aws-lambda.bad.yml')
        data = loader.get_data()
        for c in data:
            try:
                l = configuration.Lambda(loader, c, **data[c])
                self.fail('Configuration ' + l.name + ' failed to fail')
            except TypeError:
                pass

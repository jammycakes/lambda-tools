import os.path
import unittest
from lambda_tools import command

from lambda_tools.configuration import Configuration

class TestBootstrap(unittest.TestCase):

    def test_compare_yaml_and_json(self):
        s1 = command.bootstrap(os.path.join(__file__, '../aws-lambda-1.yml'))
        s2 = command.bootstrap(os.path.join(__file__, '../aws-lambda-1.json'))
        self.assertEqual(s1.get(Configuration).data, s2.get(Configuration).data)

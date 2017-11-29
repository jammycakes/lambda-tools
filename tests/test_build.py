import os.path
import unittest
import zipfile

from lambda_tools import build
from lambda_tools import configuration

class TestIgnores(unittest.TestCase):

    def setUp(self):
        root = os.path.join(os.path.dirname(__file__), 'functions')
        cfg = configuration.load(os.path.join(root, 'aws-lambda.yml'))
        ignores = cfg.functions['ignores']
        ignores.build.resolve(root)
        self.package = build.Package(ignores)

    def test_build(self):
        self.package.create()
        zf = zipfile.ZipFile(self.package.build.package)
        files = zf.namelist()
        self.assertListEqual(files, ['another.py', 'main.py'])

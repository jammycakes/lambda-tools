import unittest
from hello import handler

class Test_Hello(unittest.TestCase):

    def test_hello(self):
        result = handler(None, None)
        self.assertEqual('Hello world', result)
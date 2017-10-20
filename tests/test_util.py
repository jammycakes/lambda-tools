import unittest

from lambda_tools import util

class A:
    pass

class B:
    pass

class TestServiceLocator(unittest.TestCase):

    def test_locate_A(self):
        sl = util.ServiceLocator()
        a = sl.get(A)
        self.assertIsInstance(a, A)

    def test_locate_B_from_A(self):
        sl = util.ServiceLocator()
        sl.register(A, B)
        a = sl[A]()
        self.assertIsInstance(a, B)

    def test_locate_B_from_A_services(self):
        sl = util.ServiceLocator()
        sl.register(B, A)
        a = sl.get(A)
        b = a.services[B]()
        self.assertIsInstance(b, A)

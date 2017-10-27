import unittest

import factoryfactory

class A(factoryfactory.Serviceable):
    pass

class B(factoryfactory.Serviceable):
    pass

class C(factoryfactory.Serviceable):
    def __init__(self):
        self.a = self.services[A]()

class TestServiceLocator(unittest.TestCase):

    def test_locate_A(self):
        sl = factoryfactory.ServiceLocator()
        a = sl.get(A)
        self.assertIsInstance(a, A)

    def test_locate_B_from_A(self):
        sl = factoryfactory.ServiceLocator()
        sl.register(A, B)
        a = sl[A]()
        self.assertIsInstance(a, B)

    def test_locate_B_from_A_services(self):
        sl = factoryfactory.ServiceLocator()
        sl.register(B, A)
        a = sl.get(A)
        b = a.services[B]()
        self.assertIsInstance(b, A)

    def test_locate_singleton(self):
        sl = factoryfactory.ServiceLocator()
        sl.register(A, A, singleton=True)
        a = sl.get(A)
        b = sl.get(A)
        self.assertEqual(a, b)

    def test_locate_non_singleton(self):
        sl = factoryfactory.ServiceLocator()
        a = sl.get(A)
        b = sl.get(A)
        self.assertNotEqual(a, b)

    def test_locate_non_callable(self):
        sl = factoryfactory.ServiceLocator()
        sl.register('Hello', 'World')
        a = sl.get('Hello')
        self.assertEqual('World', a)

    def test_constructor(self):
        sl = factoryfactory.ServiceLocator()
        a = sl.get(C)
        self.assertIsInstance(a.a, A)

    def test_lambda_provider(self):
        sl = factoryfactory.ServiceLocator()
        sl.register('Hello', lambda *args, **kwargs: 'World')
        a = sl.get('Hello')
        self.assertEqual('World', a)

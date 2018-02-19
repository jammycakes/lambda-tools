import sys
import factoryfactory

class UnitTestRunner(factoryfactory.Serviceable):
    
    def run_tests(self, package, test_folder):
        print('Running tests using unittest')

        import unittest
        unittest.main(module=None, argv=['', 'discover', '-s', test_folder])


def register(services):
    """
    Registers the test runners in this module.
    """
    services.register('test-runner.unittest', UnitTestRunner, singleton=True)

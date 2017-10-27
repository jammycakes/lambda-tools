import os.path
import pip
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

import lambda_tools

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession(),
)
pip_requirements = [str(r.req) for r in requirements]

version = lambda_tools.VERSION


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main([self.pytest_args])
        sys.exit(errno)


setup(
    name='lambda_tools',
    packages=['lambda_tools'],
    version=version,
    description='A toolkit for creating and deploying Python code to AWS Lambda',
    author='James McKay',
    author_email='code@jamesmckay.net',
    keywords=['aws-lambda', 'aws'],
    url='https://github.com/jammycakes/lambda-tools',
    download_url = 'https://github.com/jammycakes/lambda-tools/archive/{0}.tar.gz'.format(version),
    license='MIT',
    install_requires=pip_requirements,
    zip_safe=False,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    entry_points={
        'console_scripts': [
            'ltools=lambda_tools.command:main'
        ]
    },
    tests_require=['pytest'],
    cmdclass = {'test': PyTest},
)
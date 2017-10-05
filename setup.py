import os.path
import pip
from setuptools import setup

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession(),
)
pip_requirements = [str(r.req) for r in requirements]

with open(os.path.join(os.path.dirname(__file__), '.version')) as f:
    version = f.read()

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
    }
)
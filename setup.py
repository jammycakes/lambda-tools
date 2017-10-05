import pip
from setuptools import setup

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession(),
)
pip_requirements = [str(r.req) for r in requirements]

setup(
    name='lambda_tools',
    packages=['lambda_tools'],
    version='0.1',
    description='A toolkit for creating and deploying Python code to AWS Lambda',
    author='James McKay',
    author_email='code@jamesmckay.net',
    keywords=['aws-lambda', 'aws'],
    url='https://github.com/jammycakes/lambda-tools',
    download_url = 'https://github.com/jammycakes/lambda-tools/archive/0.1.tar.gz',
    license='MIT',
    install_requires=pip_requirements,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'ltools=lambda_tools.command:main'
        ]
    }
)
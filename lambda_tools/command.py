import json as j
import os
import os.path
import sys

import click
from lambda_tools import factoryfactory

from . import configuration


def clean_errors(func):
    def call(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as ex:
            sys.stderr.write(str(ex) + os.linesep)
            sys.exit(1)

    return call


def bootstrap(lambda_file):
    if not lambda_file:
        default_files = ['aws-lambda.yml', 'aws-lambda.yaml', 'aws-lambda.json']
        found_files = [os.path.realpath(f) for f in default_files if os.path.isfile(f)]
        if not found_files:
            raise FileNotFoundError('No configuration file could be found.')
        lambda_file = found_files[0]
    services = factoryfactory.ServiceLocator()
    filename = os.path.realpath(lambda_file)
    folder = os.path.dirname(filename)
    config = configuration.load(filename)
    services.register(configuration.Configuration, config, singleton=True)
    return services


# ====== Command line functions ====== #

@click.group()
def main():
    pass


def _list(source, functions):
    config = bootstrap(source).get(configuration.Configuration)
    funcdefs = config.get_functions(functions)
    for func in funcdefs.values():
        func.build.resolve(config.root)
    data = dict([(key, funcdefs[key].build.package) for key in funcdefs])
    print(j.dumps(data, separators=(',', ': '), indent=2))


@main.command('list',
    help='Lists the lambda functions in the definition file'
)
@click.option('--source', '-s', default=None,
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1)
@clean_errors
def list_cmd(source, functions):
    _list(source, functions)

# ====== build command ====== #

@main.command('build',
    help='Build the specified lambda functions into packages ready for manual upload to AWS.'
)
@click.option('--source', '-s', default=None,
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.option('--terraform', is_flag=True)
@click.argument('functions', nargs=-1)
@clean_errors
def build(source, functions, terraform):
    from .build import BuildCommand
    bootstrap(source).get(BuildCommand, functions, terraform).run()
    if terraform:
        _list(source, functions)


# ====== deploy command ====== #

@main.command('deploy',
    help='Deploy the specified lambda functions to AWS.'
)
@click.option('--source', '-s', default=None,
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1
)
@clean_errors
def deploy(source, functions):
    from .deploy import DeployCommand
    bootstrap(source).get(DeployCommand, functions).run()


@main.command('version', help='Print the version number and exit.')
@clean_errors
def version():
    from lambda_tools import VERSION
    print(VERSION)

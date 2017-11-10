import click
import json as j
import os
import os.path
import sys

import factoryfactory

from . import configuration

def bootstrap(lambda_file):
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


@main.command('list',
    help='Lists the lambda functions in the definition file'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1)
def list_cmd(source, functions):
    config = bootstrap(source).get(configuration.Configuration)
    funcdefs = config.get_functions(functions)
    for func in funcdefs.values():
        func.build.resolve(config.root)
    data = dict([(key, funcdefs[key].build.package) for key in funcdefs])
    print(j.dumps(data, separators=(',', ': '), indent=2))


# ====== build command ====== #

@main.command('build',
    help='Build the specified lambda functions into packages ready for manual upload to AWS.'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1)
def build(source, functions):
    from .build import BuildCommand
    bootstrap(source).get(BuildCommand, functions).run()


# ====== deploy command ====== #

@main.command('deploy',
    help='Deploy the specified lambda functions to AWS.'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1
)
def deploy(source, functions):
    from .deploy import DeployCommand
    bootstrap(source).get(DeployCommand, functions).run()


@main.command('version', help='Print the version number and exit.')
def version():
    from lambda_tools import VERSION
    print(VERSION)
import click
import json as j
import os
import sys

@click.group()
def main():
    pass


def _process(source, functions, action, json):
    from .lambdas import load
    lambdas = load(source, functions)
    for l in lambdas:
        action(l)
    if json:
        d = dict([[l.cfg.name, l.cfg.package] for l in lambdas])
        print(j.dumps(d, separators=(',', ': '), indent=2))
    if functions and not lambdas:
        if not json:
            print('None of the specified lambda definitions were found.')
        sys.exit(1)


@main.command('list',
    help='Lists the lambda functions in the definition file'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.option('--json', '-j', is_flag=True,
    help='Output the built packages in JSON format.'
)
@click.argument('functions', nargs=-1)
def list_cmd(source, json, functions):
    _process(
        source, functions,
        lambda x: sys.stdout.write('' if json else (x.cfg.name + os.linesep)),
        json
    )

# ====== build command ====== #

@main.command('build',
    help='Build the specified lambda functions into packages ready for manual upload to AWS.'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.option('--json', '-j', is_flag=True,
    help='Output the built packages in JSON format.'
)
@click.argument('functions', nargs=-1)
def build(source, json, functions):
    _process(source, functions, lambda x: x.build(silent=json), json)


# ====== deploy command ====== #

@main.command('deploy',
    help='Deploy the specified lambda functions to AWS.'
)
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.option('--json', '-j', is_flag=True,
    help='Output the built packages in JSON format.'
)
@click.argument('functions', nargs=-1
)
def deploy(source, json, functions):
    _process(source, functions, lambda x: x.deploy(silent=json), json)


@main.command('version', help='Print the version number and exit.')
def version():
    from lambda_tools import VERSION
    print(VERSION)
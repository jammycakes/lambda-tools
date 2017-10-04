import click
import sys

@click.group()
def main():
    pass


# ====== build command ====== #

@main.command('build')
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1)
def build(source, functions):
    from .lambdas import load
    lambdas = load(source, functions)
    if functions and not lambdas:
        print('None of the specified lambda definitions were found.')
        sys.exit(1)
    for l in lambdas:
        l.build()


@main.command('deploy')
@click.option('--source', '-s', default='aws-lambda.yml',
    help='Specifies the source file containing the lambda definitions. Default aws-lambda.yml.'
)
@click.argument('functions', nargs=-1)
def deploy(source, functions):
    from .lambdas import load
    lambdas = load(source, functions)
    if functions and not lambdas:
        print('None of the specified lambda definitions were found.')
        sys.exit(1)
    for l in lambdas:
        l.deploy()

import argparse
import inspect
import os.path
import sys
import factoryfactory

from . import configuration
from .build import Package

# ====== Command base class ====== #

class Command(factoryfactory.Serviceable):

    def name(self):
        return None

    def meta(self):
        return {}

    def register_arguments(self, parser):
        pass

    def register_dependencies(self, args):
        pass

    def register(self, subarguments):
        """
        Registers a command.
        """
        name = self.name()
        if not name:
            return None
        parser = subarguments.add_parser(name, **self.meta())
        self.register_arguments(parser)
        parser.set_defaults(command=self)

    def run(self, args):
        pass


class ConfiguredCommand(Command):
    """
    A command that depends on the configuration from the YAML file.
    """

    def register_arguments(self, parser):
        parser.add_argument('--source', '-s', default=None,
            help='Specifies the source file containing the lambda definitions. '
                'Default: aws-lambda.yml or aws-lambda.json.'
        )

    def register_dependencies(self, args):
        lambda_file = args.source
        if not lambda_file:
            default_files = ['aws-lambda.yml', 'aws-lambda.yaml', 'aws-lambda.json']
            found_files = [os.path.realpath(f) for f in default_files if os.path.isfile(f)]
            if not found_files:
                raise FileNotFoundError('No configuration file could be found.')
            lambda_file = found_files[0]
        filename = os.path.realpath(lambda_file)
        folder = os.path.dirname(filename)
        config = configuration.load(filename)
        self.services.register(configuration.Configuration, config, singleton=True)


class SelectedFunctionsCommand(ConfiguredCommand):

    def register_arguments(self, parser):
        ConfiguredCommand.register_arguments(self, parser)
        parser.add_argument('functions', nargs='*',
            help='The list of lambda function names to process. If none '
            'specified, will process all the functions defined in the file.',
            metavar='function'
        )

    def process_function(self, args, function, name):
        """
        Processes a lambda function.

        :param args
            The parsed arguments object.
        @param function
            The configuration section for the function being processed.
        @param name
            The name of the function being processed.
        """
        pass

    def run(self, args):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(args.functions)
        for name in functions:
            funcdef = functions[name]
            self.process_function(args, funcdef, name)


# ====== Build command ====== #

class BuildCommand(SelectedFunctionsCommand):

    def name(self):
        return 'build'

    def meta(self):
        return {
            'description': 'Builds the specified lambda functions into packages '
                'ready for manual upload to AWS.'
        }

    def register_arguments(self, parser):
        SelectedFunctionsCommand.register_arguments(self, parser)
        parser.add_argument('--terraform', '-t', action='store_true',
            help="Accepts input and renders output in a format compatible with "
                "Terraform's external data source."
        )

    def process_function(self, args, function, name):
        package = self.services.get(Package, function, name, terraform=args.terraform)
        package.create()


# ====== Test command ====== #

class TestCommand(SelectedFunctionsCommand):

    def name(self):
        return 'test'

    def meta(self):
        return {
            'description': 'Run the unit tests on the specified functions.'
        }

    def process_function(self, args, function, name):
        package = self.services.get(Package, function, name)
        package.run_tests()


# ====== Clean command ====== #

class CleanCommand(SelectedFunctionsCommand):

    def name(self):
        return 'clean'

    def meta(self):
        return {
            'description':
                'Removes the bundle folder, and optionally the build package.'
        }

    def register_arguments(self, parser):
        SelectedFunctionsCommand.register_arguments(self, parser)
        parser.add_argument('--all', '-a', action='store_true',
            help='Remove the deployment package as well as the bundle.'
        )

    def process_function(self, args, function, name):
        package = self.services.get(Package, function, name)
        package.clean(args.all)


# ====== Deploy command ====== #

class DeployCommand(SelectedFunctionsCommand):

    def name(self):
        return 'deploy'

    def meta(self):
        return {
            'description':
                'Deploys the specified lambda functions to AWS.'
        }

    def process_function(self, args, function, name):
        from .deploy import Deployer
        package = self.services.get(Deployer, function, name)
        package.deploy()


# ====== Version command ====== #

class VersionCommand(Command):

    def name(self):
        return 'version'

    def run(self, args):
        from lambda_tools import VERSION
        print(VERSION)


# ====== Command and dependency registration ====== #

def get_command_classes():
    return (
        clazz() for clazz in globals().values()
        if inspect.isclass(clazz) and issubclass(clazz, Command) and clazz != Command
    )


def register_core_dependencies(services):
    pass


def entrypoint(args):
    service_locator = factoryfactory.ServiceLocator()
    register_core_dependencies(service_locator)

    parser = argparse.ArgumentParser(
        prog='ltools',
        description='A command line toolkit to build, test and deploy lambda functions to AWS.'
    )
    subparsers = parser.add_subparsers()

    # Get the commands to register.
    # Initially just get the commands in this module.
    # We can extend this later to allow us to search other modules
    # (e.g. if we want to implement a plugin system)
    command_classes = get_command_classes()

    for clazz in command_classes:
        command = service_locator.get(clazz)
        command.register(subparsers)

    parsed_args = parser.parse_args(args)
    if hasattr(parsed_args, 'command'):
        parsed_args.command.register_dependencies(parsed_args)
        parsed_args.command.run(parsed_args)

def main():
    entrypoint(sys.argv[1:])
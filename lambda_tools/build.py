"""
Packages the files into a folder ready to upload to AWS.

This involves:

 (a) Copy all the files into the folder.
 (b) Run pip install -r requirements.txt -t /path/to/folder
 (c) Zip it all up
"""

import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile

import factoryfactory
import pip

from . import configuration

class TestError(Exception):
    pass


class Package(factoryfactory.Serviceable):
    """
    Creates a bundled package
    """

    def __init__(self, cfg, name, terraform=False):
        """
        @param cfg
            The FunctionConfig from which the package is to be built.
        @param base_dir
            The base directory relative to which paths are to be resolved.
        @param bundle_folder
            The temporary folder into which the packgage is to be created.
        """
        self.root = self.services.get(configuration.Configuration).root
        self.name = name
        self.runtime = cfg.runtime
        self.terraform = terraform
        self.build = cfg.build
        self.build.resolve(self.root)
        self.test = cfg.test
        self.bundle_folder = cfg.build.bundle

    def copy_files(self):
        """
        Copies the files from the source folder into the bundle.
        """
        if os.path.exists(self.bundle_folder):
            shutil.rmtree(self.bundle_folder)
        shutil.copytree(
            self.build.source, self.bundle_folder,
            ignore=shutil.ignore_patterns(*self.build.ignore)
        )

    def install_requirement_file(self, requirement):
        """
        Installs the requirements specified in requirements.txt into the bundle.
        """
        stdout_redirect = sys.stderr if self.terraform else sys.stdout
        with open(requirement) as f, \
            tempfile.NamedTemporaryFile(mode='w+t') as t:
            for line in f:
                s = line.strip()
                s = re.sub(r'^-e\s+', '', s)
                t.file.write(s + os.linesep)
            t.flush()
            compile_args = [ '--compile' if self.build.compile_dependencies else '--no-compile' ]
            if self.build.use_docker:
                cmd = [
                    'docker', 'run',
                    '-v', os.path.realpath(t.name) + ':/requirements.txt',
                    '-v', os.path.realpath(self.bundle_folder) + ':/bundle',
                    '--rm', 'python:3.6.3',
                    'pip', 'install', '-r', '/requirements.txt', '-t', '/bundle'
                ]
            else:
                cmd = [ 'pip', 'install', '-r', t.name, '-t', self.bundle_folder ]
            subprocess.run(cmd + compile_args, stdout=stdout_redirect)

        #
        # pip doesn't preserve timestamps when installing files.
        # I think it's supposed to, but it doesn't seem to work.
        # Therefore we'll set the timestamps of all downloaded files to
        # the timestamp of the requirements.txt file.
        #
        times = (
            os.path.getatime(requirement),
            os.path.getmtime(requirement)
        )
        for dirname, subdirs, files in os.walk(self.bundle_folder):
            for filename in files + subdirs:
                filepath = os.path.join(dirname, filename)
                os.utime(filepath, times)


    def install_requirements(self, requirements):
        for requirement in requirements or []:
            self.install_requirement_file(requirement.file)


    def create_archive(self):
        """
        Creates the archive file.
        """
        dirname = os.path.dirname(self.build.package)
        os.makedirs(dirname, exist_ok=True)
        base_name, fmt = os.path.splitext(self.build.package)
        fmt = fmt.replace(os.path.extsep, '') or 'zip'
        shutil.make_archive(base_name, fmt, self.bundle_folder, './', True)

    def create(self):
        """
        Performs all the above steps to create the bundle.
        """
        try:
            self.copy_files()
            self.install_requirements(self.build.requirements)
            self.create_archive()
        finally:
            if not self.test:
                self.remove_bundle_folder()

    def run_tests(self):
        """
        Runs the unit tests.

        @returns
            true if tests were run, otherwise false.
        """
        if not self.test:
            return False

        if not os.path.isdir(self.bundle_folder):
            raise TestError('Function {0} has not yet been built.'.format(self.name))

        from . import test_runners
        test_runners.register(self.services)

        test_runner = self.services.get("test-runner." + self.test.runner)
        if not test_runner:
            raise TestError('Test runner {0} was not found.'.format(self.test.runner))

        test_folder = os.path.join(self.bundle_folder, 'test')
        if os.path.isdir(test_folder):
            shutil.rmtree(test_folder)
        shutil.copytree(
            self.test.source, test_folder,
            ignore=shutil.ignore_patterns(*self.test.ignore)
        )
        self.install_requirements(self.test.requirements)

        sys.path.insert(0, self.bundle_folder)
        try:
            test_runner.run_tests(self, test_folder)
        finally:
            del sys.path[0]
        return True

    def remove_bundle_folder(self):
        """
        Removes the bundle folder.
        """
        print('Removing bundle folder ' + self.bundle_folder)
        if os.path.isdir(self.bundle_folder):
            shutil.rmtree(self.bundle_folder)
        elif os.path.exists(self.bundle_folder):
            os.unlink(self.bundle_folder)
        self.bundle_folder = None

    def remove_deployment_package(self):
        """
        Removes the deployment package.
        """
        print('Removing build package ' + self.build.package)
        if os.path.isdir(self.build.package):
            shutil.rmtree(self.build.package)
        elif os.path.exists(self.build.package):
            os.unlink(self.build.package)

    def clean(self, all):
        """
        Removes the bundle folder and deployment package if specified.
        """
        print(str(all))
        self.remove_bundle_folder()
        if all:
            self.remove_deployment_package()


class BuildCommand(factoryfactory.Serviceable):

    def __init__(self, functions, terraform):
        self.functions = functions
        self.terraform = terraform

    def run(self):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(self.functions)
        for name in functions:
            funcdef = functions[name]
            package = self.services.get(Package, funcdef, name, terraform=self.terraform)
            package.create()


class TestCommand(factoryfactory.Serviceable):

    def __init__(self, functions):
        self.functions = functions

    def run(self):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(self.functions)
        for name in functions:
            funcdef = functions[name]
            package = self.services.get(Package, funcdef, name)
            package.run_tests()


class CleanCommand(factoryfactory.Serviceable):

    def __init__(self, functions, all):
        self.functions = functions
        self.all = all

    def run(self):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(self.functions)
        for name in functions:
            funcdef = functions[name]
            package = self.services.get(Package, funcdef, name)
            package.clean(self.all)
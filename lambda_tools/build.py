"""
Packages the files into a folder ready to upload to AWS.

This involves:

 (a) Copy all the files into the folder.
 (b) Run pip install -r requirements.txt -t /path/to/folder
 (c) Zip it all up
"""

import os.path
import re
import shutil
import subprocess
import tempfile
from distutils import dir_util

import factoryfactory
import pip

from . import configuration


class Package(factoryfactory.Serviceable):
    """
    Creates a bundled package
    """

    def __init__(self, cfg, bundle_folder=None):
        """
        @param cfg
            The FunctionConfig from which the package is to be built.
        @param base_dir
            The base directory relative to which paths are to be resolved.
        @param bundle_folder
            The temporary folder into which the packgage is to be created.
        """
        self.root = self.services.get(configuration.Configuration).root
        self.runtime = cfg.runtime
        self.build = cfg.build
        self.build.resolve(self.root)
        if bundle_folder:
            self.bundle_folder = os.path.join(self.root, bundle_folder)
        else:
            self.bundle_folder = None

    def create_bundle_folder(self):
        """
        Ensures that the bundle folder exists.
        """
        self.bundle_folder = self.bundle_folder or os.path.realpath(tempfile.mkdtemp())
        os.makedirs(self.bundle_folder, exist_ok=True)

    def copy_files(self):
        """
        Copies the files from the source folder into the bundle.
        """
        dir_util.copy_tree(self.build.source, self.bundle_folder)


    def install_requirement_file(self, requirement):
        """
        Installs the requirements specified in requirements.txt into the bundle.
        """
        with open(requirement) as f, \
            tempfile.NamedTemporaryFile(mode='w+t') as t:
            for line in f:
                s = line.strip()
                s = re.sub(r'^-e\s+', '', s)
                t.file.write(s + os.linesep)
            t.flush()
            compile_arg = '--compile' if self.build.compile_dependencies else '--no-compile'
            if self.build.use_docker:
                subprocess.run([
                    'docker', 'run',
                    '-v', os.path.realpath(t.name) + ':/requirements.txt',
                    '-v', os.path.realpath(self.bundle_folder) + ':/bundle',
                    '--rm', 'python:3.6.3',
                    'pip', 'install',
                    compile_arg, '-r', '/requirements.txt', '-t', '/bundle'
                ])
            else:
                pip.main([
                    'install', compile_arg,
                    '-r', t.name,
                    '-t', self.bundle_folder
                ])
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


    def install_requirements(self):
        for requirement in self.build.requirements or []:
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

    def remove_bundle_folder(self):
        """
        Removes the bundle folder.
        """
        shutil.rmtree(self.bundle_folder)
        self.bundle_folder = None

    def create(self):
        """
        Performs all the above steps to create the bundle.
        """
        self.create_bundle_folder()
        try:
            self.install_requirements()
            self.copy_files()
            self.create_archive()
        finally:
            self.remove_bundle_folder()


class BuildCommand(factoryfactory.Serviceable):

    def __init__(self, functions):
        self.functions = functions

    def run(self):
        config = self.services.get(configuration.Configuration)
        functions = config.get_functions(self.functions)
        for name in functions:
            funcdef = functions[name]
            package = self.services.get(Package, funcdef)
            package.create()

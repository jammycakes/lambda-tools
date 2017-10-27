"""
Packages the files into a folder ready to upload to AWS.

This involves:

 (a) Copy all the files into the folder.
 (b) Run pip install -r requirements.txt -t /path/to/folder
 (c) Zip it all up
"""

from distutils import dir_util
import os
import os.path
import pip
import re
import shutil
import subprocess
import tempfile

class Package(object):

    def __init__(self, cfg, bundle_folder=None, silent=True):
        """
        Creates an instance of the Package class.

        @param cfg
            The configuration object for the lambda.
        @param bundle_folder
            The folder into which the bundle is to be created.
            If none specified, a temporary folder will be created.
        @param silent
            `True` to suppress output to the console. Otherwise `False`.
        """
        self.cfg = cfg
        self.bundle_folder = bundle_folder
        self.use_docker = self.cfg.use_docker and bool(shutil.which('docker'))
        self.silent = silent

    def create_bundle_folder(self):
        """
        Ensures that the bundle folder exists.
        """
        self.bundle_folder = os.path.realpath(self.bundle_folder or tempfile.mkdtemp())
        os.makedirs(self.bundle_folder, exist_ok=True)

    def copy_files(self):
        """
        Copies the files from the source folder into the bundle.
        """
        dir_util.copy_tree(self.cfg.source, self.bundle_folder)

    def install_requirements(self):
        """
        Installs the requirements specified in requirements.txt into the bundle.
        """
        if not self.cfg.requirements:
            return
        with open(self.cfg.requirements) as f, \
                tempfile.NamedTemporaryFile(mode='w+t') as t:
            for line in f:
                s = line.strip()
                s = re.sub(r'^-e\s+', '', s)
                t.file.write(s + os.linesep)
            t.flush()
            if self.use_docker:
                output = subprocess.DEVNULL if self.silent else None
                subprocess.run([
                    'docker', 'run',
                    '-v', os.path.realpath(t.name) + ':/requirements.txt',
                    '-v', os.path.realpath(self.bundle_folder) + ':/bundle',
                    '--rm', 'python:3.6.3',
                    'pip', 'install', '-r', '/requirements.txt', '-t', '/bundle'
                ], stdout=output)
            else:
                pip.main(['install', '-r', t.name, '-t', self.bundle_folder])

    def exec_lambda(self, test_data):
        if self.use_docker:
            subprocess.run([
                'docker', 'run',
                '-v', os.path.realpath(self.bundle_folder) + ':/var/task',
                'lambci/lambda:python3.6',
                self.cfg.handler
            ])

    def create_archive(self):
        """
        Creates the archive file.
        """
        dirname = os.path.dirname(self.cfg.package)
        os.makedirs(dirname, exist_ok=True)
        base_name, fmt = os.path.splitext(self.cfg.package)
        fmt = fmt.replace(os.path.extsep, '') or 'zip'
        shutil.make_archive(base_name, fmt, self.bundle_folder, './', True)

    def remove_bundle_folder(self):
        """
        Removes the bundle folder.
        """
        shutil.rmtree(self.bundle_folder)

    def create(self):
        """
        Performs all the above steps to create the bundle.
        """
        self.create_bundle_folder()
        try:
            self.copy_files()
            self.install_requirements()
            self.create_archive()
        finally:
            self.remove_bundle_folder()

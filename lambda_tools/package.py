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

def package(source_folder, requirements_file, target, use_docker=True, silent=True):
    """
    Creates a package ready to upload to AWS Lambda.

    @param source_folder
        The source code folder to upload.
    @param requirements_file
        The requirements file to use to specify the dependencies.
    @param target
        The file in which to save the target
    @param use_docker
        True to use Docker (if available) to create the bundle, otherwise False.
        You will need to use Docker if you are running on OSX or Windows and
        one or more of your dependencies includes C source code which has to be
        compiled. This is because binaries compiled on OSX or Windows will not
        run on the Linux instances that are used to run Lambda code in AWS.
    """
    bundle = tempfile.mkdtemp()
    try:
        dir_util.copy_tree(source_folder, bundle)
        if requirements_file:
            with open(requirements_file) as f, tempfile.NamedTemporaryFile(mode='w+t') as t:
                for line in f:
                    s = line.strip()
                    s = re.sub(r'^-e\s+', '', s)
                    t.file.write(s + os.linesep)
                t.flush()
                if use_docker and shutil.which('docker'):
                    output= subprocess.DEVNULL if silent else None
                    subprocess.run([
                        'docker', 'run',
                        '-v', os.path.realpath(t.name) + ':/requirements.txt',
                        '-v', os.path.realpath(bundle) + ':/bundle',
                        '-it', '--rm', 'python:3.6.3',
                        'pip', 'install', '-r', '/requirements.txt', '-t', '/bundle'
                    ], stdout=output)
                else:
                    pip.main(['install', '-r', t.name, '-t', bundle])

        dirname = os.path.dirname(target)
        os.makedirs(dirname, exist_ok=True)
        base_name, fmt = os.path.splitext(target)
        fmt = fmt.replace(os.path.extsep, '') or 'zip'

        shutil.make_archive(base_name, fmt, bundle, './', True)

    finally:
        shutil.rmtree(bundle)

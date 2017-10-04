"""
Packages the files into a folder ready to upload to AWS.

This involves:

 (a) Copy all the files into the folder.
 (b) Run pip install -r requirements.txt -t /path/to/folder
 (c) Zip it all up
"""

from distutils import dir_util
import os
import pip
import re
import shutil
import sys
import tempfile
import zipfile

def package(source_folder, requirements_file, target):
    """
    Creates a package ready to upload to AWS Lambda.

    @param source_folder
        The source code folder to upload.
    @param requirements_file
        The requirements file to use to specify the dependencies.
    @param target
        The file in which to save the target
    """
    bundle = tempfile.mkdtemp()
    try:
        dir_util.copy_tree(source_folder, bundle)
        if requirements_file:
            with open(requirements_file) as f:
                with tempfile.NamedTemporaryFile(mode='w+t') as t:
                    for line in f:
                        s = line.strip()
                        s = re.sub(r'^-e\s+', '', s)
                        t.file.write(s + os.linesep)
                    t.flush()
                    pip.main(['install', '-r', t.name, '-t', bundle])

        dirname = os.path.dirname(target)
        os.makedirs(dirname, exist_ok=True)
        base_name, fmt = os.path.splitext(target)
        fmt = fmt.replace(os.path.extsep, '') or 'zip'

        shutil.make_archive(base_name, fmt, bundle, './', True)

    finally:
        shutil.rmtree(bundle)


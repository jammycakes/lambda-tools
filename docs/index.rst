.. lambda-tools documentation master file, created by
   sphinx-quickstart on Sat Nov 18 20:30:50 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to lambda-tools's documentation!
========================================

Lambda-tools is a little utility that helps you to build and deploy code
to AWS Lambda.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Quick start
-----------

To install Lambda Tools, type:

.. code:: bash

    pip install lambda-tools

Note: you need to be using Python 3.5 or later (3.6 preferred).

Now create a file in the root directory of your project called ``aws-lambda.yml``.
A minimal lambda definition file will look something like this:

.. code:: yaml

    version: 1

    functions:
      hello_world:
        build:
          source: hello_world

        deploy:
          handler: hello.handler
          role: service-role/lambda-role
          region: eu-west-2

*Note: I am assuming here that you already have a role called ``lambda-role``
configured in your AWS account. If you haven't, use the AWS console to create
one.*

Create a folder next to your lambda function called ``hello_world`` and create
a Python script within it called ``hello.py``. Copy and paste the following
contents into it:

.. code:: python

    def handler(event, context):
        return 'Hello world'

Now run:

.. code:: bash

    ltools build

You will see a file created next to your source directory called
``hello_world.zip``. This is the package that will be uploaded to AWS Lambda.

Now run:

.. code:: bash

    ltools deploy

All being well, this will deploy your code to AWS.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

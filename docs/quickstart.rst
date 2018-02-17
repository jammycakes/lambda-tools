.. _quickstart:

Quick start
===========

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
          role: lambda-role
          region: eu-west-2

Create a folder next to your lambda function called ``hello_world`` and create
a Python script within it called ``hello.py``. Copy and paste the following
contents into it:

.. code:: python

    def handler(event, context):
        return 'Hello world'

If you don't already have an IAM role set up to run AWS Lambda functions, create
one in the AWS console:

 * Select the IAM service under "Services"
 * Under "Roles", select "Create Role"
 * Under "AWS Service" choose "Lambda" then click "Next: Permissions"
 * Select any policies that you want to apply to the role, then choose
   "Next: Review"
 * Give the role a name — in this case, "lambda-role"
 * Click "Create role"

Now run:

.. code:: bash

    ltools build

You will see a file created next to your source directory called
``hello_world.zip``. This is the package that will be uploaded to AWS Lambda.

Now run:

.. code:: bash

    ltools deploy

All being well, this will deploy your code to AWS, in the ``eu-west-2`` (London)
region.

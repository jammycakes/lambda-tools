.. _commands:

Command line instructions
=========================

Lambda Tools is run from the command line by using the ``ltools`` command.
If you type ``ltools --help``, you will be shown a list of the available
commands. These are as follows.

ltools build
------------

Usage: ``ltools build [OPTIONS] [FUNCTIONS]...``

  Build the specified lambda functions into packages ready for manual upload
  to AWS.

Options:
  -s, --source TEXT  Specifies the source file containing the lambda definitions. Default: ``aws-lambda.yml``.
  --terraform        Renders output suitable for Terraform's external data source.
  --help             Show this message and exit.

ltools deploy
-------------

Usage: ``ltools deploy [OPTIONS] [FUNCTIONS]...``

  Deploy the specified lambda functions to AWS.

Options:
  -s, --source TEXT  Specifies the source file containing the lambda
                     definitions. Default ``aws-lambda.yml``.
  --help             Show this message and exit.

.. note::
    The lambda functions being deployed must already have been built using
    ``ltools build``.

ltools list
-----------

Usage: ``ltools list [OPTIONS] [FUNCTIONS]...``

  Lists the lambda functions in the definition file.

Options:
  -s, --source TEXT  Specifies the source file containing the lambda
                     definitions. Default aws-lambda.yml.
  --help             Show this message and exit.

ltools version
--------------

Usage: ``ltools version [OPTIONS]``

  Print the version number and exit.

Options:
  --help  Show this message and exit.

.. _terraform:

Using Lambda Tools with Terraform
=================================

If you are using `Terraform`__ to build up your
infrastructure, you may want to use Lambda Tools to create the zip files to be
uploaded to AWS.

__ https://www.terraform.io/

Lambda Tools includes a "Terraform mode" switch in ``ltools build`` which allows
you to use it in conjunction with Terraform's `external data source`__.

__ https://www.terraform.io/docs/providers/external/data_source.html

The setup for the external data source will look something like this:

.. code::

    data "external" "lambda" {
      program = [
        "ltools",
        "build",
        "--terraform",
        "-s",
        "${path.module}/aws-lambda.yml",
        "${var.lambda_name}",
      ]
    }

    resource "aws_lambda_function" "my_lambda" {
      function_name = "${var.lambda_name}"

      filename         = "${lookup(data.external.lambda.result, "${var.lambda_name}")}"
      source_code_hash = "${base64sha256(file(lookup(data.external.lambda.result, "${var.lambda_name}")))}"
      role             = "${aws_iam_role.github-user-management.arn}"

      handler = "main.handler"
      runtime = "python3.6"
      timeout = 30
    }

What this is doing is passing an extra parameter, ``--terraform``, to
``ltools build``, which instructs it to render its output in the format required
by Terraform's external data source — specifically, a JSON dictionary of strings.
The dictionary so returned will list the names of the functions which have been
built, together with the paths to their respective build artefacts. You can then
use Terraform's `lookup function`__ to get the filename to be passed to the
`aws_lambda_function`__ resource.

__ https://www.terraform.io/docs/configuration/interpolation.html#lookup-map-key-default-
__ https://www.terraform.io/docs/providers/aws/r/lambda_function.html

.. note::
    The ``--terraform`` option also redirects any output from ``ltools build``
    from ``stdout`` to ``stderr``. This output will only be rendered by Terraform
    if the build fails for any reason.
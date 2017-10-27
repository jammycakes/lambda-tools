lambda-tools
============

[![Build Status][shield-travis]][info-travis]

A toolkit for creating and deploying Python code to AWS Lambda

This is a simple Python package that will let you build and deploy AWS Lambda
functions quickly and easily.

It supports the creation of multiple lambdas from a single codebase.

Lambda definition file
----------------------

Create a file called `aws-lambda.yml` in the root directory of your project.
This will contain your lambda function's definitions.

Sample `aws-lambda.yml` file:

```yml
hello_world:
  description: A basic Hello World handler
  region: eu-west-1
  runtime: python3.6
  handler: hello.handler
  memory: 128
  timeout: 3

  # Role, VPC, subnets, security groups and KMS key are all specified by name.
  role: service-role/NONTF-lambda
  vpc: My VPC
  subnets:
    - Public subnet
    - Private subnet
  security_groups:
    - allow_database
  kms_key: aws/lambda

  tags:
    wibble: wobble
  environment:
    foo: bar
    # Empty value here will cause the environment variable to be passed through
    baz:

  tracing: PassThrough | Active
  dead_letter: [ARN of SQS queue or SNS topic]

  # Folder and file locations. All are relative to the .yml file.
  # This is the source code for your lambda.
  source: src/hello_world
  # This is your requirements.txt file for any packages used by the lambda.
  requirements: requirements.txt
  # This is where the built package will be saved before being uploaded to AWS.
  package: build/hello_world.zip
```

You can define multiple lambdas in a single file. The properties are as follows:

| Property          | Default         | Description |
|-------------------|---------------  |-------------|
| `handler`         | **Required.**   | The name of the Python module and function which will handle the lambda invocation. Given in the format `module.handler`. |
| `role`            | **Required.**   | The name of the IAM role under which the function will run. |
| `source`          | **Required.**   | The folder containing the function's source code. This is relative to the `aws-lambda.yml` file. |
| `dead_letter`     |                 | The ARN of the SQS queue or SNS topic used as a dead letter queue for failed lambda invocations. |
| `description`     |                 | A short text description of the function. |
| `environment`     |                 | Environment variables to be configured for the function. Any blank environment variables that you specify here will be taken from the environment passed to the `ltools` command. |
| `kms_key`         |                 | The name of the KMS key used to encrypt the environment variables. If not specified, the default `aws/lambda` KMS key will be used. |
| `memory`          | 128             | The amount of memory allocated to the function, in gigabytes. Must be a multiple of 64 gigabytes. |
| `package`         | `{source}.zip`  | The filename where the function's bundled package should be saved, ready to upload to AWS. This is relative to the `aws-lambda.yml` file. |
| `region`          |                 | The AWS region into which the function is to be deployed. If not specified, it will be taken from the environment variables or the configuration information set using `aws configure`. |
| `requirements`    |                 | The requirements.txt file specifying any Python packages that need to be installed along with your lambda. This is relative to the `aws-lambda.yml` file. |
| `runtime`         | `python3.6`     | The language runtime used by the function. Note that while you may specify any language supported by AWS, only `python3.6` (the default) is currently fully supported by lambda_tools. |
| `security_groups` |                 | The names of the security groups which should apply to the function when running in a VPC. |
| `subnets`         |                 | The names of the subnets into which the function should be placed. |
| `tags`            |                 | The tags to apply to the function. |
| `timeout`         | 3               | The timeout for the function to run, in seconds. |
| `tracing`         |                 | The tracing settings for your function. Should be set to either `PassThrough` or `Active`. |
| `use_docker`      | `false`         | Build the lambda in a Docker container. |
| `vpc`             |                 | The name of the VPC into which the function should be launched. You don't need to specify this unless it can not be uniquely identified from the names of the security groups and subnets. |

A few points worth noting here:

 * `handler`, `source` and `role` are all required.
 * If you want to run your lambda in a VPC, you must specify both `subnets` and
    `security_groups`. You don't have to specify `vpc` as well unless you have
    identically named subnets or security groups in multiple VPCs and need to
    disambiguate them.
 * `role`, `vpc`, `subnets`, `security_groups` and `kms_key` are all specified
    by name rather than ID or ARN.
 * `dead_letter` does not yet support specifying SNS topics or SQS queues by
    name. See [GitHub issue 3](https://github.com/jammycakes/lambda-tools/issues/3)
    for the latest status on this one.
 * All folder and file names are relative to your `aws-lambda.yml` file.
 * You will normally not need to use Docker, unless you are building your
   lambda function on OSX or Windows **and** some of your dependencies are
   written partly in C. If you get "Invalid ELF header" errors in AWS after
   uploading your lambda to AWS, change this setting to `true`. For more
   information see
   [this article](https://medium.freecodecamp.org/escaping-lambda-function-hell-using-docker-40b187ec1e48).

Command line instructions
-------------------------

 * `ltools build`: builds some or all of the lambda functions specified in the
   `aws-lambda.yml` file in the current directory.
 * `ltools deploy`: deploys some or all of the lambda functions specified in
   the `aws-lambda.yml` file in the current directory.


[info-travis]:   https://travis-ci.org/jammycakes/lambda-tools
[shield-travis]: https://img.shields.io/travis/jammycakes/lambda-tools.svg
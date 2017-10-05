lambda-tools
============

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

You can define multiple lambdas in a single file. However, note the following:

 * `handler`, `source` and `role` are all required.
 * If you want to run your lambda in a VPC, you must specify both `subnets` and
    `security_groups`. You don't have to specify `vpc` as well unless you have
    identically named subnets or security groups in multiple VPCs and need to
    disambiguate them.
 * `role`, `vpc`, `subnets`, `security_groups` and `kms_key` are all specified
    by name rather than ID or ARN.
 * All folder and file names are relative to your `aws-lambda.yml` file.

Command line instructions
-------------------------

 * `ltools build`: builds some or all of the lambda functions specified in the
   `aws-lambda.yml` file in the current directory.
 * `ltools deploy`: deploys some or all of the lambda functions specified in
   the `aws-lambda.yml` file in the current directory.
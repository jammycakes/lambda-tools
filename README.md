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
# Version number is required and should be set to 1.
version: 1

functions:
  hello_world:
    runtime: python3.6

    # The build section is required
    build:
      # source is required
      source: src/hello_world

      # Optional settings
      compile_dependencies: false
      package: build/hello_world.zip
      use_docker: false

      requirements:
        - file: requirements.txt

    # The deploy section is optional if you want to use another mechanism
    # (e.g. Terraform) to deploy your function to AWS Lambda
    deploy:
      # These settings are required
      handler: hello.handler
      role: service-role/NONTF-lambda

      # Optional settings
      description: A basic Hello World handler
      memory_size: 128
      package: build/hello_world.zip
      region: eu-west-1
      timeout: 3

      dead_letter_config:
        target:
          sqs: SQS queue name; alternatively, an SNS topic can be specified.

      environment:
        variables:
          foo: bar
          # Empty value here will cause the environment variable to be passed through
          baz:

      kms_key:
        name: aws/lambda

      tags:
        Account: Marketing
        Application: Newsletters

      tracing_config:
        mode: PassThrough | Active

      vpc_config:
        name: My VPC
        subnets:
          - name: Public subnet
          - name: Private subnet
        security_groups:
          - name: allow_database
```

Definitiion file reference
--------------------------

Your `aws-lambda.yml` file starts with a number indicating which version of the
configuration schema you are using. This should be version 1.

The `functions` section then contains your function definitions. The name of
each entry within this section gives the name of your function.

Each function contains two sub-sections.

### The `runtime` parameter

The `runtime` parameter is optional and defaults to `python3.6`. It indicates
which language runtime is used by the function.

  * Note that while you may specify any language supported by AWS, only
    `python3.6` (the default) is currently fully supported by lambda_tools.
    Support for other AWS-supported runtimes is planned.

### The `build` section

The `build` section is required. It tells `ltools` where to find the source
files for your lambda and how to build it. The parameters are as follows:

 * `source` **(Required)**: The folder containing your function's source code.
    This is specified relative to the `aws-lambda.yml` file.

 * `requirements`: A list of requirements files specifying the Python packages
    to be downloaded from PyPI for inclusion with your function.

 * `compile_dependencies`: Compile the Python files in dependent packages into
    .pyc files. *Default: false.*
    * By default, `.py` files in your dependencies are not compiled into `.pyc`
    files. This may increase the startup time of your lambda function,
    especially if the number of dependencies that you have specified is large
    but it does mean that the same build will produce exactly the same binary.
    This is important, for example, if you are using `ltools` in conjunction
    with Terraform, which looks for changes in your build output.

 * `package`: The filename where your function's bundled package should be
    saved, ready to upload to AWS. This is relative to the `aws-lambda.yml`
    file.
    * If not specified, it will be saved into a zip file next to the folder
    containing your source code.

 * `use_docker`: Build the lambda in a Docker container. *Default: false.*
    * You will normally not need to use Docker, unless you are building your
    lambda function on OSX or Windows **and** some of your dependencies are written
    partly in C. If you get "Invalid ELF header" errors in AWS after uploading your
    lambda to AWS, change this setting to `true`. For more information see
[this article](https://medium.freecodecamp.org/escaping-lambda-function-hell-using-docker-40b187ec1e48).

### The `deploy` section

The `deploy` section is optional. You only need it if you are going to be
using `ltools` itself to deploy your function to AWS Lambda. If you are using
a different mechanism, such as Terraform, for deployment, you can omit it.

The parameters are as follows:

 * `handler` **(Required)**: The function's entry point into your code.
    For Python, this is specified in the format `module.handler`.

 * `role` **(Required)**: The name of the IAM role attached to the lambda
    function. This determines who or what can run your function, as well as what
    resources it can access.

 * `source` **(Required)**: The folder containing your function's source code.
    This is specified relative to the `aws-lambda.yml` file.

 * `description`: A short description of what your function does.

 * `memory_size`: The amount of memory that your function can use at runtime,
    in gigabytes. Must be a multiple of 64 gigabytes. *Default: 128*.

 * `region`: The AWS region into which your function is to be deployed.
    * If not specified, it will be taken from either the environment variables
      or the configuration information that you have set using `aws configure`.

 * `timeout`: The maximum time, in seconds, that your function is allowed to run
    before being terminated. *Default: 3 seconds*.

 * `dead_letter_config`: Configures your lambda function's dead letter queue, to
 which notifications of failed invocations are sent. This can be either an SNS
 topic or an SQS queue, and it can be specified either by name or by ARN.
    * It can be configured in one of the following ways:

    ```yaml
      dead_letter_config:
        target_arn: (the ARN of your queue or topic)

      dead_letter_config:
        target:
          sns: (the name of your SNS topic)

      dead_letter_config:
        target:
          sqs: (the name of your SQS queue)
    ```

 * `environment`: The environment variables to be passed to your function.
    It is configured as follows:
    ```yaml
      environment:
        variables:
          VARIABLE: some value
          PASSTHROUGH_VARIABLE:
    ```
    Variables whose value is left blank will be passed through to the function
      configuration from the environment which invokes `ltools`.


 * `kms_key`: The KMS key used to encrypt the environment variables. This can be
    specified either by name or by ARN:

    ```yaml
      kms_key:
        name: aws/lambda

      kms_key:
        arn: "arn:aws:kms:eu-west-1:123456789012:key:01234567-89ab-cdef-0123-456789abcdef"
    ```

    If no key is specified, the default key, `aws/lambda`, will be used.

 * `tags`: The tags to be assigned to your lambda function. For example:

    ```yaml
      tags:
        Account: marketing
        Application: newsletters
    ```

 * `tracing_config`: The tracing settings for your application. This contains a
    single argument, `mode`:

    ```yaml
      tracing_config:
        mode: PassThrough
    ```
    `mode` can be set to either `PassThrough` or `Active`. If `PassThrough`,
    Lambda will only trace the request from an upstream service if it contains a
    tracing header with `sampled=1`. If `Active`, Lambda will respect any tracing
    header it receives from an upstream service. If no tracing header is received,
    Lambda will call X-Ray for a tracing decision.

 * `vpc_config`: Add this section if you want your lambda function to access your
    VPC. You will need to specify subnets and security groups:
    ```yaml
      vpc_config:
        subnets:
          - id: subnet-12345678
          - name: public-subnet
          - another-subnet
        security_groups:
          - id: sg-12345678
          - name: some-group
          - another-group
    ```
    Security groups and subnets can be specified either by ID or by name. As a
    shortcut, you can omit `name:` when specifying it by name.

    If you have two or more security groups or subnets with the same name in
    different VPCs, you will also need to specify the ID or name of the VPC in
    order to disambiguate them:

    ```yaml
      vpc_config:
        name: My VPC
        subnets:
          - id: subnet-12345678
          - name: public-subnet
          - another-subnet
        security_groups:
          - id: sg-12345678
          - name: some-group
          - another-group
    ```


Command line instructions
-------------------------

 * `ltools build`: builds some or all of the lambda functions specified in the
   `aws-lambda.yml` file in the current directory.
 * `ltools deploy`: deploys some or all of the lambda functions specified in
   the `aws-lambda.yml` file in the current directory.
 * `ltools list`: lists the lambda functions defined in your `aws-lambda.yml`
   file.
 * `ltools version`: displays the version number and exits.



[info-travis]:   https://travis-ci.org/jammycakes/lambda-tools
[shield-travis]: https://img.shields.io/travis/jammycakes/lambda-tools.svg
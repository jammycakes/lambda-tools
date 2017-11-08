"""
This module defines some mock objects that we can use in place of boto3 calls.
"""

MOCK_ACCOUNT_ID = 123456789012
MOCK_AWS_REGION = "eu-west-1"

mock_clients = {}


def client(name):
    def register(cls):
        mock_clients[name.lower()] = cls
        return cls
    return register


@client('ec2')
class MockEc2Client(object):

    def __init__(self, *args, **kwargs):
        pass

    def describe_vpcs(self, *args, **kwargs):
        return {
            "Vpcs": [
                {
                    "VpcId": "vpc-12345678",
                    "Tags": [
                        { "Key": "Name", "Value": "My VPC" }
                    ]
                }
            ]
        }

    def describe_subnets(self, *args, **kwargs):
        return {
            "Subnets": [
                {
                    "SubnetId": "subnet-12345678",
                    "Tags": [
                        { "Key": "Name", "Value": "Public subnet" }
                    ]
                },
                {
                    "SubnetId": "subnet-11111111",
                    "Tags": [
                        { "Key": "Name", "Value": "Private subnet" }
                    ]
                },
            ]
        }

    def describe_security_groups(self, *args, **kwargs):
        return {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "allow_database",
                    "VpcId": "vpc-12345678"
                }
            ]
        }

@client('kms')
class MockKmsClient(object):

    def __init__(self, *args, **kwargs):
        pass

    def describe_key(self, *args, **kwargs):
        keyid = "12345678-dead-beef-face-cafe12345678"
        return {
            "KeyMetadata": {
                "KeyId": keyid,
                "AWSAccountId": str(MOCK_ACCOUNT_ID),
                "Arn": "arn:aws:kms:{0}:{1}:key/{2}".format(MOCK_AWS_REGION, MOCK_ACCOUNT_ID, keyid),
            }
        }


@client('lambda')
class MockLambdaClient(object):

    def __init__(self, *args, **kwargs):
        pass

    def create_function(self, *args, **kwargs):
        result = kwargs.copy()
        result.update({
            "FunctionArn": "arn:aws:lambda:{0}:{1}:function:{2}".format(
                MOCK_AWS_REGION,
                MOCK_ACCOUNT_ID,
                kwargs['FunctionName']
            )
        })
        return result

    def update_function_configuration(self, *args, **kwargs):
        return self.create_function(*args, **kwargs)

    def update_function_code(self, *args, **kwargs):
        pass

    def untag_resource(self, *args, **kwargs):
        pass

    def tag_resource(self, *args, **kwargs):
        pass

    def get_function_configuration(*args, **kwargs):
        pass


@client('sts')
class MockStsClient(object):

    def __init__(self, *args, **kwargs):
        pass

    def get_caller_identity(self):
        return {
            "Account": MOCK_ACCOUNT_ID
        }

class MockSession(object):

    def __init__(self, region_name=None, *args, **kwargs):
        self.region_name = region_name or MOCK_AWS_REGION

    def client(self, service, region_name=None, *args, **kwargs):
        c = mock_clients.get(service)
        if c:
            result = c(region_name=self.region_name, *args, **kwargs)
            result.region_name = self.region_name or region_name
            return result
        else:
            return None

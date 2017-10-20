"""
Miscellaneous utility files
"""

def assert_dict(data, name):
    if isinstance(data, dict):
        return data
    else:
        raise ValueError(name + ' needs to be a dictionary')

# ====== Inversion of Control ====== #

class ServiceLocator(object):

    def __init__(self):
        self.providers = {}

    def register(self, service, provider):
        self.providers[service] = provider

    def __getitem__(self, service):
        service_locator = self
        provider = self.providers.get(service, service)

        def create_service(*args, **kwargs):
            result = provider(*args, **kwargs)
            result.services = service_locator
            return result

        if callable(provider):
            return create_service
        else:
            return service

    def get(self, service, *args, **kwargs):
        return self[service](*args, **kwargs)


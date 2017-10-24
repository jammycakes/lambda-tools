"""
Miscellaneous utility files
"""

def assert_dict(data, name):
    if isinstance(data, dict):
        return data
    else:
        raise ValueError(name + ' needs to be a dictionary')

# ====== Inversion of Control ====== #

class Serviceable(object):
    services = None


class ServiceLocator(object):

    def __init__(self):
        self.providers = {}
        self.singletons = {}


    def _get_instantiator(self, provider):

        def instantiate(*args, **kwargs):
            if not callable(provider):
                return provider
            else:
                result = provider(*args, **kwargs)
                if isinstance(result, Serviceable):
                    result.services = self
                return result

        return instantiate


    def register(self, service, provider, singleton=False):
        """
        Registers a service provider for a given service.

        @param service
            A key that identifies the service being registered.
        @param provider
            This is either the service being registered, or a callable that will
            either instantiate it or return it.
        @param singleton
            Indicates that the service is to be registered as a singleton.
            This is only relevant if the provider is a callable. Services that
            are not callable will always be registered as singletons.
        """

        def get_singleton(*args, **kwargs):
            result = self.singletons.get(service)
            if not result:
                instantiator = self._get_instantiator(provider)
                result = instantiator(*args, **kwargs)
                self.singletons[service] = result
            return result

        # Providers are always registered in self.providers  as callable methods

        if not callable(provider):
            self.providers[service] = lambda *args, **kwargs: provider
        elif singleton:
            self.providers[service] = get_singleton
        else:
            self.providers[service] = self._get_instantiator(provider)


    def __getitem__(self, service):
        """
        Returns a function that returns the requested service.
        """
        provider = self.providers.get(service)
        if provider:
            return provider
        elif callable(service):
            return self._get_instantiator(service)
        else:
            return lambda *args, **kwargs: service


    def get(self, service, *args, **kwargs):
        return self[service](*args, **kwargs)


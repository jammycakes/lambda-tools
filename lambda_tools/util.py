"""
Miscellaneous utility files
"""

def assert_dict(data, name):
    if isinstance(data, dict):
        return data
    else:
        raise ValueError(name + ' needs to be a dictionary')

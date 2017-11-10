"""
Contains classes and functions for mapping raw JSON/YAML output onto an
object hierarchy.
"""

class MappingError(Exception):
    pass


class Field:

    def __init__(self, required=False, nullable=False, default=None):
        self.nullable = bool(nullable)
        self.default = default
        self.required = bool(required)

    def parse(self, value, field_name):
        if value == None and not self.nullable:
            raise MappingError('Value "{0}" can not be null.'.format(field_name))
        return value

    def get_default(self, field_name):
        if self.required:
            raise MappingError('Required value "{0}" was not provided.'.format(field_name))
        else:
            return self.default


class StringField(Field):

    def __init__(self, **kwargs):
        Field.__init__(self, **kwargs)

    def parse(self, value, field_name):
        if value != None and not isinstance(value, str):
            raise MappingError('Value "{0}" must be a string.'.format(field_name))
        return Field.parse(self, value, field_name)


class IntField(Field):

    def __init__(self, **kwargs):
        Field.__init__(self, **kwargs)

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if value != None:
            try:
                return int(value)
            except ValueError:
                raise MappingError('Value "{0}" must be convertible to an integer.'.format(field_name))


class BoolField(Field):

    def __init__(self, **kwargs):
        Field.__init__(self, **kwargs)

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if value != None:
            try:
                return bool(value)
            except ValueError:
                raise MappingError('Value "{0}" must be convertible to a Boolean.'.format(field_name))


class ChoiceField(Field):

    def __init__(self, choices, **kwargs):
        self.choices = choices
        Field.__init__(self, **kwargs)

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if value != None and value not in self.choices:
            raise MappingError('Value "{0}" must be one of: {1}.'.format(
                field_name,
                ', '.join((str(choice) for choice in self.choices))
            ))
        return value


class ListField(Field):

    def __init__(self, item_field=None, default=[], **kwargs):
        Field.__init__(self, default=default, **kwargs)
        self.item_field = item_field or Field()

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if isinstance(value, str) or isinstance(value, dict):
            # Strings and dicts are iterable but we want to disallow them.
            raise MappingError('Value "{0}" must be a list.'.format(field_name))
        elif hasattr(value, '__iter__'):
            return [
                self.item_field.parse(item, '{0}[{1}]'.format(field_name, index))
                for index, item in enumerate(value)
            ]
        else:
            raise MappingError('Value "{0}" must be a list.'.format(field_name))


class DictField(Field):

    def __init__(self, item_field=None, default={}, **kwargs):
        Field.__init__(self, default=default, **kwargs)
        self.item_field = item_field or Field()

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if isinstance(value, dict):
            return dict([
                (key, self.item_field.parse(
                    value[key], '{0}[{1}]'.format(field_name, key)
                ))
                for key in value
            ])
        else:
            raise MappingError('Value "{0}" must be a dictionary.'.format(field_name))

    def __getitem__(self, index):
        """
        Placeholder method to make it look like a dict to comfort pylint
        """
        return None


class ClassField(Field):

    def __init__(self, cls, default_field=None, **kwargs):
        self.cls = cls
        self.default_field = default_field
        Field.__init__(self, **kwargs)

    def parse(self, value, field_name):
        value = Field.parse(self, value, field_name)
        if self.default_field and not isinstance(value, dict):
            return parse(self.cls, { self.default_field: value }, field_name)
        else:
            return parse(self.cls, value, field_name)



def parse(clz, data, field_name=None):

    if not isinstance(clz, type):
        raise MappingError('Target class must be a type.')

    import inspect
    members = dict(inspect.getmembers(clz, lambda m: issubclass(type(m), Field)))

    if isinstance(data, dict):
        instance = clz()
        for key in data:
            field = members.pop(key, None)
            if not field:
                raise MappingError('Unrecognised value "{0}".'.format(key))
            value = field.parse(data[key], key)
            setattr(instance, key, value)
        for key in members:
            field = members[key]
            value = field.get_default(key)
            setattr(instance, key, value)
        if hasattr(clz, 'validate') and callable(clz.validate) and not isinstance(clz.validate, Field):
            msg = clz.validate(instance)
            if msg:
                raise MappingError(msg)
        return instance
    else:
        if field_name:
            raise MappingError('Field {0} must be a dictionary.'.format(field_name))
        else:
            raise MappingError('Data must be a dictionary.')
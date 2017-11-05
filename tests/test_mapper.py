import unittest
from lambda_tools import mapper


FAMOUS_FIVE = ['Dick', 'Julian', 'George', 'Anne', 'Timmy']

class StringFieldEntity:
    hello = mapper.StringField()


class TestStringField(unittest.TestCase):

    def test_simple_mapping(self):
        result = mapper.parse(StringFieldEntity, { 'hello': 'world' })
        self.assertEqual('world', result.hello)
        self.assertIsInstance(result, StringFieldEntity)

    def test_simple_mapping_with_default(self):
        result = mapper.parse(StringFieldEntity, { })
        self.assertEqual(None, result.hello)

    def test_simple_mapping_with_unknown_value(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(StringFieldEntity, { 'goodbye': 'test'})
        )

    def test_simple_mapping_with_non_dict(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(StringFieldEntity, 'Hello world')
        )


class RequiredStringFieldEntity:
    hello = mapper.StringField(required=True)


class TestRequiredStringField(unittest.TestCase):

    def test_missing_required_field(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(RequiredStringFieldEntity, { })
        )


class IntFieldEntity:
    count = mapper.IntField(default=100)


class TestIntField(unittest.TestCase):

    def test_int_field(self):
        result = mapper.parse(IntFieldEntity, { 'count': 10 })
        self.assertEqual(result.count, 10)

    def test_missing_int_field(self):
        result = mapper.parse(IntFieldEntity, { })
        self.assertEqual(result.count, 100)

    def test_int_as_string(self):
        result = mapper.parse(IntFieldEntity, { 'count': '10' })
        self.assertEqual(result.count, 10)


class BoolFieldEntity:
    active = mapper.BoolField()


class TestBoolField(unittest.TestCase):

    def test_true(self):
        result = mapper.parse(BoolFieldEntity, { 'active': True })
        self.assertEqual(result.active, True)

    def test_false(self):
        result = mapper.parse(BoolFieldEntity, { 'active': False })
        self.assertEqual(result.active, False)


class ChoiceFieldEntity:
    name = mapper.ChoiceField(FAMOUS_FIVE)


class TestChoiceField(unittest.TestCase):

    def test_valid(self):
        result = mapper.parse(ChoiceFieldEntity, { 'name': 'Julian' })

    def test_invalid(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ChoiceFieldEntity, { 'name': 'Jack' })
        )

    def test_missing(self):
        result = mapper.parse(ChoiceFieldEntity, { })
        self.assertEqual(None, result.name)


class ListFieldEntity:
    names = mapper.ListField(mapper.StringField())


class TestListField(unittest.TestCase):

    def test_valid(self):
        result = mapper.parse(ListFieldEntity, { 'names': FAMOUS_FIVE })
        self.assertListEqual(result.names, FAMOUS_FIVE)

    def test_set(self):
        names = set(FAMOUS_FIVE)
        result = mapper.parse(ListFieldEntity, { 'names': names })
        self.assertListEqual(result.names, list(names))

    def test_empty_list(self):
        result = mapper.parse(ListFieldEntity, { 'names': [] })
        self.assertListEqual(result.names, [])

    def test_invalid_list(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ListFieldEntity, { 'names': range(5) })
        )

    def test_string(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ListFieldEntity, { 'names': '5' })
        )

    def test_dict(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ListFieldEntity, { 'names': {} })
        )


class DictFieldEntity:
    environment = mapper.DictField(mapper.StringField())


class TestDictField(unittest.TestCase):

    def test_valid(self):
        result = mapper.parse(DictFieldEntity, { 'environment': { 'one': 'two' } })
        self.assertDictEqual(result.environment, { 'one': 'two' })

    def test_invalid_dict(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(DictFieldEntity, { 'environment': { 'one': [] } })
        )


class ClassFieldEntity:
    five = mapper.ClassField(ChoiceFieldEntity)


class TestChoiceField(unittest.TestCase):

    def test_valid(self):
        result = mapper.parse(ClassFieldEntity, {
            'five': {
                'name': 'Julian'
            }
        })
        self.assertEqual(result.five.name, 'Julian')

    def test_invalid(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ClassFieldEntity, {
                'five': {
                    'name': 'Philip'
                }
            })
        )


class ListClassFieldEntity:
    five = mapper.ListField(mapper.ClassField(ChoiceFieldEntity))


class TestListClassField(unittest.TestCase):

    def test_valid(self):
        result = mapper.parse(ListClassFieldEntity, {
            'five': [
                { 'name': 'Julian' },
                { 'name': 'Dick' },
                { 'name': 'George' },
                { 'name': 'Anne' },
                { 'name': 'Timmy' }
            ]
        })
        names = sorted([x.name for x in result.five])
        self.assertListEqual(names, sorted(FAMOUS_FIVE))

    def test_invalid(self):
        self.assertRaises(
            mapper.MappingError,
            lambda: mapper.parse(ListClassFieldEntity, {
                'five': [
                    { 'name': 'Peter' },
                    { 'name': 'Janet' },
                    { 'name': 'Jack' },
                    { 'name': 'Barbara' },
                    { 'name': 'George' },
                    { 'name': 'Pam' },
                    { 'name': 'Colin' },
                ]
            })
        )


class ClassWithDefaultFieldEntity:
    five = mapper.ClassField(ChoiceFieldEntity, default_field='name')


class TestClassWithDefaultField(unittest.TestCase):

    def test_default_field(self):
        result = mapper.parse(ClassWithDefaultFieldEntity, { 'five': 'George' })
        self.assertEqual(result.five.name, 'George')
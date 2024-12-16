import datetime
import unittest
from django.test import TestCase
from main.apps.core.utils.json_serializable import remove_non_json_serializable


class JsonSerializationTestCase(TestCase):

    def test_remove_datetime(self):
        original_data = {
            "name": "Alice",
            "courses": {"math", "history", "chemistry", datetime.datetime.now()},
            "created_at": datetime.datetime.now(),
            "friends": [
                "Bob",
                "Charlie",
                {"name": "Eve", "joined": datetime.datetime.now()},
            ],
        }

        expected_data = {
            "name": "Alice",
            "courses": {"math", "history", "chemistry"},
            "friends": [
                "Bob",
                "Charlie",
                {"name": "Eve"},
            ],
        }

        filtered_data = remove_non_json_serializable(original_data)
        self.assertEqual(filtered_data, expected_data, "Filtered data does not match the expected result")

    def test_remove_lambda(self):
        data = {'key1': 'value1', 'key2': lambda x: x + 1}
        expected_data = {'key1': 'value1'}

        cleaned_data = remove_non_json_serializable(data)
        self.assertEqual(cleaned_data, expected_data)

    def test_nested_dict(self):
        data = {
            'key1': 'value1',
            'key2': {'subkey1': 'subvalue1', 'subkey2': lambda x: x * 2},
        }
        expected_data = {'key1': 'value1', 'key2': {'subkey1': 'subvalue1'}}

        cleaned_data = remove_non_json_serializable(data)
        self.assertEqual(cleaned_data, expected_data)

    def test_list(self):
        data = ['value1', 42, lambda x: x * 2]
        expected_data = ['value1', 42]

        cleaned_data = remove_non_json_serializable(data)
        self.assertEqual(cleaned_data, expected_data)

    def test_tuple(self):
        data = ('value1', 42, lambda x: x * 2)
        expected_data = ('value1', 42)

        cleaned_data = remove_non_json_serializable(data)
        self.assertEqual(cleaned_data, expected_data)

    def test_set(self):
        data = {'value1', 42, lambda x: x * 2}
        expected_data = {'value1', 42}

        cleaned_data = remove_non_json_serializable(data)
        self.assertEqual(cleaned_data, expected_data)


if __name__ == '__main__':
    unittest.main()

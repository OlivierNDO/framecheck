import unittest
import pandas as pd
from src.frame_check import Schema, ValidationResult
from src.column_checks import ColumnCheck, ColumnExistsCheck


class DummyCheck(ColumnCheck):
    def __init__(self, column_name, messages=None, indices=None, raise_on_fail=True):
        super().__init__(column_name, raise_on_fail)
        self._messages = messages or []
        self._indices = indices or set()

    def validate(self, series: pd.Series) -> dict:
        return {"messages": self._messages, "failing_indices": self._indices}


class TestSchema(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z'],
            'extra': [10, 20, 30]
        })

    def test_validation_success(self):
        checks = [DummyCheck('a'), DummyCheck('b')]
        schema = Schema(checks)
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validation_with_errors(self):
        checks = [DummyCheck('a', messages=['fail a'], indices={1})]
        schema = Schema(checks)
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn('fail a', result.errors)
        self.assertIn(1, result.get_invalid_rows(self.df).index)

    def test_validation_with_warnings(self):
        checks = [DummyCheck('a', messages=['warn a'], indices={1}, raise_on_fail=False)]
        schema = Schema(checks)
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertIn('warn a', result.warnings)

    def test_missing_column_error(self):
        checks = [DummyCheck('missing_column')]
        schema = Schema(checks)
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("does not exist in DataFrame", result.errors[0])

    def test_only_defined_columns_blocks_extras(self):
        checks = [DummyCheck('a'), DummyCheck('b')]
        schema = Schema(checks, disallow_extra_columns=True)
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("Unexpected columns", result.errors[0])

    def test_ignore_extra_columns_when_allowed(self):
        checks = [DummyCheck('a'), DummyCheck('b')]
        schema = Schema(checks, disallow_extra_columns=False)
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)

    def test_invalid_return_type_from_check(self):
        class BadCheck(ColumnCheck):
            def validate(self, series: pd.Series):
                return "not a dict"

        schema = Schema([BadCheck('a')])
        with self.assertRaises(TypeError):
            schema.validate(self.df)


if __name__ == '__main__':
    unittest.main()

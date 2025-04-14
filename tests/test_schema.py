import unittest
import pandas as pd
from framecheck.frame_check import Schema, ValidationResult
from framecheck.column_checks import ColumnCheck
from framecheck.dataframe_checks import DefinedColumnsOnlyCheck


class DummyCheck(ColumnCheck):
    def __init__(self, column_name, messages=None, indices=None, raise_on_fail=True):
        super().__init__(column_name, raise_on_fail)
        self._messages = messages or []
        self._indices = indices or set()

    def validate(self, series: pd.Series) -> dict:
        return {"messages": self._messages, "failing_indices": self._indices}


class TestSchema(unittest.TestCase):
    """Tests Schema integration with both column and dataframe-level checks."""

    def setUp(self):
        self.df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z'],
            'extra': [10, 20, 30]
        })

    def test_validation_success(self):
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validation_with_errors(self):
        schema = Schema(
            column_checks=[DummyCheck('a', messages=['fail a'], indices={1})],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn('fail a', result.errors)
        self.assertIn(1, result.get_invalid_rows(self.df).index)

    def test_validation_with_warnings(self):
        schema = Schema(
            column_checks=[DummyCheck('a', messages=['warn a'], indices={1}, raise_on_fail=False)],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertIn('warn a', result.warnings)

    def test_missing_column_error(self):
        schema = Schema(
            column_checks=[DummyCheck('missing_column')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("does not exist in DataFrame", result.errors[0])

    def test_only_defined_columns_blocks_extras(self):
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("Unexpected columns", result.errors[0])

    def test_ignore_extra_columns_when_not_checked(self):
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)

    def test_invalid_return_type_from_check(self):
        class BadCheck(ColumnCheck):
            def validate(self, series: pd.Series):
                return "not a dict"

        schema = Schema(
            column_checks=[BadCheck('a')],
            dataframe_checks=[]
        )
        with self.assertRaises(TypeError):
            schema.validate(self.df)
            
    def test_dataframe_check_warn_only(self):
        class DummyDFCheck:
            def __init__(self):
                self.raise_on_fail = False
    
            def validate(self, df):
                return {"messages": ["warn from df check"], "failing_indices": set()}
    
        schema = Schema(
            column_checks=[],
            dataframe_checks=[DummyDFCheck()]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertIn("warn from df check", result.warnings)



if __name__ == '__main__':
    unittest.main()

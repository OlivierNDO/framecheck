"""Unit tests for frame_check.Schema"""
import unittest
import pandas as pd
from framecheck.frame_check import Schema, ValidationResult
from framecheck.column_checks import ColumnCheck
from framecheck.dataframe_checks import DefinedColumnsOnlyCheck


class DummyCheck(ColumnCheck):
    """
    A simple test double for ColumnCheck used in unit tests to simulate
    validation behavior with predefined messages and failing indices.
    """
    def __init__(self, column_name, messages=None, indices=None, raise_on_fail=True):
        """
        Initialize DummyCheck with static validation results.

        Parameters
        ----------
        column_name : str
            Name of the column this check applies to.
        messages : list[str], optional
            List of validation messages to return.
        indices : set[int], optional
            Set of row indices considered as failures.
        raise_on_fail : bool, default=True
            Whether validation should raise an exception on failure.
        """
        super().__init__(column_name, raise_on_fail)
        self._messages = messages or []
        self._indices = indices or set()

    def validate(self, series: pd.Series) -> dict:
        """
        Return predefined validation output regardless of input.

        Parameters
        ----------
        series : pd.Series
            Ignored input series.

        Returns
        -------
        dict
            Dictionary with 'messages' and 'failing_indices' keys.
        """
        return {"messages": self._messages, "failing_indices": self._indices}



class TestSchema(unittest.TestCase):
    """
    Tests Schema integration with both column and dataframe-level checks,
    validating error/warning aggregation, missing columns, and schema behavior.
    """
    def setUp(self):
        """Initialize a sample DataFrame with expected and extra columns."""
        self.df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z'],
            'extra': [10, 20, 30]
        })

    def test_validation_success(self):
        """Test passes when all checks succeed with no messages."""
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validation_with_errors(self):
        """Test fails when a column check returns an error message."""
        schema = Schema(
            column_checks=[DummyCheck('a', messages=['fail a'], indices={1})],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn('fail a', result.errors)
        self.assertIn(1, result.get_invalid_rows(self.df).index)

    def test_validation_with_warnings(self):
        """Test passes with warning messages when raise_on_fail is False."""
        schema = Schema(
            column_checks=[DummyCheck('a', messages=['warn a'], indices={1}, raise_on_fail=False)],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertIn('warn a', result.warnings)

    def test_missing_column_error(self):
        """Test fails when a column in the check is missing from the DataFrame."""
        schema = Schema(
            column_checks=[DummyCheck('missing_column')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("does not exist in DataFrame", result.errors[0])

    def test_only_defined_columns_blocks_extras(self):
        """Test fails when extra columns exist and are not explicitly allowed."""
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])]
        )
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.assertIn("Unexpected columns", result.errors[0])

    def test_ignore_extra_columns_when_not_checked(self):
        """Test passes when extra columns are not checked and no restrictions are applied."""
        schema = Schema(
            column_checks=[DummyCheck('a'), DummyCheck('b')],
            dataframe_checks=[]
        )
        result = schema.validate(self.df)
        self.assertTrue(result.is_valid)

    def test_invalid_return_type_from_check(self):
        """Test raises TypeError when a check returns a non-dict result."""
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
        """Test passes with warnings when a dataframe-level check fails with raise_on_fail=False."""
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

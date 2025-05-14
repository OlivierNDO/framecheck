"""Unit tests for dataframe_checks.py"""
import unittest
import pandas as pd
from framecheck.dataframe_checks import (
    ColumnComparisonCheck,
    CustomCheck,
    DefinedColumnsOnlyCheck, 
    ExactColumnsCheck,
    IsEmptyCheck,
    NoNullsCheck,
    NotEmptyCheck,
    RowCountCheck,
    UniquenessCheck
)


class TestColumnComparisonCheck(unittest.TestCase):
    """
    Test suite for ColumnComparisonCheck class, verifying column comparison
    functionality with various operators and data types.
    """
    
    def setUp(self):
        """
        Setup test dataframes for different data types and edge cases.
        """
        # Numeric comparison dataframe
        self.numeric_df = pd.DataFrame({
            'a': [1, 5, 10, None, 7, 0, -5],
            'b': [2, 5, 3, 8, None, 0, -10],
            'c': ["1", "5", "10", None, "7", "0", "-5"]  # String representations of numbers
        })
        
        # Date comparison dataframe
        self.date_df = pd.DataFrame({
            'start_date': ['2023-01-01', '2023-02-01', '2023-03-01', None, '2023-05-01', 'invalid'],
            'end_date': ['2023-01-31', '2023-01-15', '2023-04-01', '2023-04-30', None, '2023-06-01'],
            'date_obj': [pd.Timestamp('2023-01-01'), pd.Timestamp('2023-02-01'), 
                        pd.Timestamp('2023-03-01'), None, pd.Timestamp('2023-05-01'), pd.NaT]
        })
        
        # String comparison dataframe
        self.string_df = pd.DataFrame({
            'first_name': ['Alice', 'Bob', 'Charlie', None, 'Eve', ''],
            'last_name': ['Adams', 'Baker', 'Collins', 'Davis', None, 'Franklin'],
            'mixed_data': [1, 'text', True, None, 3.14, pd.Timestamp('2023-01-01')]
        })
        
        # Mixed type dataframe
        self.mixed_df = pd.DataFrame({
            'numeric': [1, 2, 3, 4, 5],
            'string': ['1', '2', '3', '4', '5'],
            'boolean': [True, True, False, True, False]
        })
        
        # Empty dataframe
        self.empty_df = pd.DataFrame()
        
    def test_date_before(self):
        """Test '<' operator with date columns."""
        check = ColumnComparisonCheck('start_date', '<', 'end_date', comparison_type='datetime')
        result = check.validate(self.date_df)
        # start_date < end_date should be false for [2023-02-01 < 2023-01-15] (index 1)
        # and indices with None/invalid (3, 4, 5)
        expected_failing = {1, 3, 4, 5}
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_date_after(self):
        """Test '>' operator with date columns."""
        check = ColumnComparisonCheck('end_date', '>', 'start_date', comparison_type='datetime')
        result = check.validate(self.date_df)
        # end_date > start_date should be false for [2023-01-15 > 2023-02-01] (index 1)
        # and index 3 (None in start_date) and index 4 (None in end_date) and index 5 (invalid date)
        expected_failing = {1, 3, 4, 5}
        self.assertEqual(result['failing_indices'], expected_failing)
        
    def test_infer_datetime_comparison_type(self):
        """Test that comparison_type is inferred as datetime and fails correctly."""
        df = pd.DataFrame({
            'left': ['2023-01-03'],  # later date
            'right': ['2023-01-02']  # earlier date
        })
        check = ColumnComparisonCheck('left', '<', 'right')  # should infer datetime
        result = check.validate(df)
        self.assertEqual(result['failing_indices'], {0})
        self.assertIn("left", result['messages'][0])
        self.assertIn("<", result['messages'][0])

    def test_numeric_greater_than(self):
        """Test '>' operator with numeric columns."""
        check = ColumnComparisonCheck('a', '>', 'b')
        result = check.validate(self.numeric_df)
        # a > b should be true for [10 > 3] (index 2)
        # Rows with None values should fail (indices 3, 4)
        # Indices 0, 1, 5, 6 fail because a is not > b
        expected_failing = {0, 1, 3, 4, 5}  # Index 6 passes (-5 > -10)
        self.assertEqual(result['failing_indices'], expected_failing)
        self.assertTrue(len(result['messages']) > 0)

    def test_numeric_less_than(self):
        """Test '<' operator with numeric columns."""
        check = ColumnComparisonCheck('a', '<', 'b')
        result = check.validate(self.numeric_df)
        # a < b should be true for [1 < 2] (index 0)
        # Rows with None values should fail (indices 3, 4)
        # Indices 1, 2, 5, 6 fail because a is not < b
        expected_failing = {1, 2, 3, 4, 5, 6}  # Index 6 fails (-5 < -10 is false)
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_numeric_equals(self):
        """Test '==' operator with numeric columns."""
        check = ColumnComparisonCheck('a', '==', 'b')
        result = check.validate(self.numeric_df)
        # a == b should be true for [5 == 5] (index 1) and [0 == 0] (index 5)
        expected_failing = {0, 2, 3, 4, 6}
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_numeric_not_equals(self):
        """Test '!=' operator with numeric columns."""
        check = ColumnComparisonCheck('a', '!=', 'b')
        result = check.validate(self.numeric_df)
        # a != b should be false for [5 != 5] (index 1) and [0 != 0] (index 5)
        expected_failing = {1, 3, 4, 5}
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_missing_right_column(self):
        """Test behavior when right column doesn't exist."""
        check = ColumnComparisonCheck('a', '>', 'missing_col')
        result = check.validate(self.numeric_df)
        self.assertIn("does not exist for comparison", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())

    def test_numeric_string_comparison(self):
        """Test comparison between numeric column and string representation."""
        # This should coerce string to numeric for comparison
        check = ColumnComparisonCheck('a', '==', 'c', comparison_type='numeric')
        result = check.validate(self.numeric_df)
        # All values should match their string representations
        expected_failing = {3}  # Only rows with None values should fail
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_mixed_type_comparison(self):
        """Test comparison between columns of different types."""
        check = ColumnComparisonCheck('numeric', '==', 'string', comparison_type='numeric')
        result = check.validate(self.mixed_df)
        # All values should match their string representations
        expected_failing = set()
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_boolean_comparison(self):
        """Test comparison with boolean values."""
        check = ColumnComparisonCheck('numeric', '>', 'boolean')
        result = check.validate(self.mixed_df)
        # 1 > True (False), 2 > True (True), 3 > False (True), 4 > True (True), 5 > False (True)
        expected_failing = {0}
        self.assertEqual(result['failing_indices'], expected_failing)
    
    def test_missing_column(self):
        """Test behavior when column doesn't exist."""
        check = ColumnComparisonCheck('missing_column', '>', 'a')
        result = check.validate(self.numeric_df)
        self.assertIn("does not exist for comparison", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())

    def test_invalid_operator(self):
        """Test that invalid operators raise ValueError."""
        with self.assertRaises(ValueError):
            ColumnComparisonCheck('a', 'invalid_operator', 'b')

    def test_null_handling(self):
        """Test handling of null values in comparison."""
        # Both columns have nulls but in different rows
        check = ColumnComparisonCheck('a', '>', 'b')
        result = check.validate(self.numeric_df)
        # Rows with null in either column should fail
        self.assertIn(3, result['failing_indices'])  # null in column a
        self.assertIn(4, result['failing_indices'])  # null in column b
        
    def test_string_comparison(self):
        """Test string comparisons."""
        check = ColumnComparisonCheck('first_name', '!=', 'last_name')
        result = check.validate(self.string_df)
        # They should all be different except for None values
        expected_failing = {3, 4}
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_string_greater_than(self):
        """Test '>' operator with string columns (lexicographical comparison)."""
        check = ColumnComparisonCheck('first_name', '>', 'last_name')
        result = check.validate(self.string_df)
        # Lexicographical comparison - in this specific case:
        # 'Alice' > 'Adams' is TRUE (A=A, but l>d)
        # 'Bob' > 'Baker' is TRUE (B=B, but o>a)
        # 'Charlie' > 'Collins' is FALSE (C=C, h<o)
        # None comparison fails
        # 'Eve' > None fails
        # '' > 'Franklin' is FALSE
        expected_failing = {2, 3, 4, 5}  # Indices 0 and 1 pass lexicographical comparison
        self.assertEqual(result['failing_indices'], expected_failing)
        
    def test_type_error_during_operator_comparison(self):
        """Test TypeError raised during direct comparison logic."""
        df = pd.DataFrame({
            'a': [lambda x: x],  # a function — not comparable
            'b': [42]
        })
        check = ColumnComparisonCheck('a', '>', 'b')  # This will hit operator > between function and int
        result = check.validate(df)
        self.assertIn(0, result['failing_indices'])

    def test_type_inference(self):
        """Test type inference when no explicit type is provided."""
        # Should infer datetime type from column name
        check = ColumnComparisonCheck('start_date', '<', 'end_date')
        result = check.validate(self.date_df)
        # Should still identify the failures from the date_before test
        expected_failing = {1, 3, 4, 5}
        self.assertEqual(result['failing_indices'], expected_failing)

    def test_invalid_date_handling(self):
        """Test handling of invalid date formats."""
        # Modified dataframe with explicitly invalid date
        df = pd.DataFrame({
            'start': ['2023-01-01', 'not-a-date'],
            'end': ['2023-01-31', '2023-02-01']
        })
        check = ColumnComparisonCheck('start', '<', 'end', comparison_type='datetime')
        result = check.validate(df)
        # The invalid date row should fail
        self.assertIn(1, result['failing_indices'])

    def test_empty_dataframe(self):
        """Test behavior with empty dataframe."""
        check = ColumnComparisonCheck('a', '>', 'b')
        result = check.validate(self.empty_df)
        self.assertIn("does not exist for comparison", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())

    def test_custom_description(self):
        """Test custom error description."""
        custom_desc = "Price must exceed cost"
        check = ColumnComparisonCheck('a', '>', 'b', description=custom_desc)
        result = check.validate(self.numeric_df)
        self.assertIn(custom_desc, result['messages'][0])

    def test_warn_only_parameter(self):
        """Test that raise_on_fail parameter works correctly."""
        # This is more relevant in the FrameCheck context but ensures the parameter is passed through
        check = ColumnComparisonCheck('a', '>', 'b', raise_on_fail=False)
        self.assertFalse(check.raise_on_fail)

    def test_all_comparison_operators(self):
        """Test all comparison operators with a simple case."""
        df = pd.DataFrame({
            'x': [5, 5, 5, 5, 5, 5],
            'y': [3, 5, 7, 3, 5, 7]
        })
        
        # Corrected expected results for each operator
        # TRUE means the check passes, FALSE means the check fails
        operators = {
            '>': [True, False, False, True, False, False],  # 5 > 3 (T), 5 > 5 (F), 5 > 7 (F)
            '>=': [True, True, False, True, True, False],   # 5 >= 3 (T), 5 >= 5 (T), 5 >= 7 (F)
            '<': [False, False, True, False, False, True],  # 5 < 3 (F), 5 < 5 (F), 5 < 7 (T)
            '<=': [False, True, True, False, True, True],   # 5 <= 3 (F), 5 <= 5 (T), 5 <= 7 (T)
            '==': [False, True, False, False, True, False], # 5 == 3 (F), 5 == 5 (T), 5 == 7 (F)
            '!=': [True, False, True, True, False, True]    # 5 != 3 (T), 5 != 5 (F), 5 != 7 (T)
        }
        
        for op, expected_results in operators.items():
            check = ColumnComparisonCheck('x', op, 'y')
            result = check.validate(df)
            
            # Calculate expected failing indices - these are where expected_results is FALSE
            expected_failing = {i for i, passes in enumerate(expected_results) if not passes}
            
            self.assertEqual(result['failing_indices'], expected_failing, 
                            f"Failed for operator '{op}': expected {expected_failing}, got {result['failing_indices']}")

    def test_type_coercion_edge_cases(self):
        """Test edge cases in type coercion."""
        df = pd.DataFrame({
            'a': ['0', '1', '2', 'true', 'false', 'NaN', ''],
            'b': [0, 1, 2, True, False, float('nan'), 0]
        })
        
        # Test numeric coercion
        check = ColumnComparisonCheck('a', '==', 'b', comparison_type='numeric')
        result = check.validate(df)
        
        # '0'==0, '1'==1, '2'==2 should pass
        # 'true'==True might fail depending on implementation (should be 'true'->NaN->fail)
        # 'false'==False might fail too
        # 'NaN'->NaN != NaN (NaN is never equal to anything, including NaN)
        # '' might convert to 0 or NaN depending on implementation
        
        # At minimum, we expect the first three to pass
        self.assertNotIn(0, result['failing_indices'])
        self.assertNotIn(1, result['failing_indices'])
        self.assertNotIn(2, result['failing_indices'])
        
        # And 'NaN' should definitely fail the comparison with NaN
        self.assertIn(5, result['failing_indices'])

    def test_comparison_with_different_dtypes(self):
        """Test comparisons between columns with different pandas dtypes."""
        df = pd.DataFrame({
            'int_col': pd.Series([1, 2, 3], dtype='int64'),
            'float_col': pd.Series([1.0, 2.0, 3.5], dtype='float64'),
            'str_col': pd.Series(['1', '2', '3.5'], dtype='object')
        })
        
        # Integer to float comparison
        check = ColumnComparisonCheck('int_col', '==', 'float_col')
        result = check.validate(df)
        expected_failing = {2}  # Only 3 != 3.5 should fail
        self.assertEqual(result['failing_indices'], expected_failing)
        
        # String to int with numeric conversion
        check = ColumnComparisonCheck('str_col', '==', 'int_col', comparison_type='numeric')
        result = check.validate(df)
        expected_failing = {2}  # '3.5' != 3 should fail
        self.assertEqual(result['failing_indices'], expected_failing)


class TestCustomCheck(unittest.TestCase):
    """
    Test suite for CustomCheck, validating row-wise logic with custom functions
    and verifying both default and user-defined descriptions.
    """
    def test_custom_check_passes(self):
        """Test custom check passes with all rows valid."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = CustomCheck(function=lambda row: row['a'] > 0)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_custom_check_fails(self):
        """Test custom check fails for a row not meeting condition."""
        df = pd.DataFrame({'a': [1, -2, 3]})
        check = CustomCheck(function=lambda row: row['a'] > 0)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertEqual(result['failing_indices'], {1})

    def test_custom_check_description_auto(self):
        """Test default failure message when not provided."""
        df = pd.DataFrame({'a': [1, -2]})
        check = CustomCheck(function=lambda row: row['a'] > 0)
        result = check.validate(df)
        self.assertIn("Custom check failed", result['messages'][0])

    def test_custom_check_description_custom(self):
        """Test custom failure message is included in results."""
        df = pd.DataFrame({'a': [0, -1]})
        check = CustomCheck(
            function=lambda row: row['a'] > 0,
            description="a must be greater than 0"
        )
        result = check.validate(df)
        self.assertIn("a must be greater than 0", result['messages'][0])

    def test_all_rows_fail(self):
        """Test all rows fail custom check condition."""
        df = pd.DataFrame({'a': [-1, -2, -3]})
        check = CustomCheck(function=lambda row: row['a'] > 0)
        result = check.validate(df)
        self.assertEqual(result['failing_indices'], {0, 1, 2})

    def test_all_rows_pass(self):
        """Test all rows pass custom check condition."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = CustomCheck(function=lambda row: row['a'] > 0)
        result = check.validate(df)
        self.assertEqual(result['failing_indices'], set())


class TestDefinedColumnsOnlyCheck(unittest.TestCase):
    """
    Test suite for DefinedColumnsOnlyCheck, ensuring no unexpected columns exist
    beyond those explicitly allowed.
    """
    def test_passes_when_no_extra_columns(self):
        """Test passes when no unexpected columns are present."""
        df = pd.DataFrame({'a': [1], 'b': [2]})
        check = DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_when_extra_columns_present(self):
        """Test fails when unexpected columns exist in the DataFrame."""
        df = pd.DataFrame({'a': [1], 'b': [2], 'extra': [3]})
        check = DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("Unexpected columns", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())
        
    def test_serialize_defined_columns_check(self):
        """Test the serialization of DefinedColumnsOnlyCheck."""
        check = DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])
        result = DefinedColumnsOnlyCheck._serialize_defined_columns_check(check)
        self.assertEqual(set(result['expected_columns']), {'a', 'b'})



class TestExactColumnsCheck(unittest.TestCase):
    """
    Test suite for ExactColumnsCheck, verifying exact match of column names and order.
    """
    def setUp(self):
        """Set expected column names used across tests."""
        self.expected = ['a', 'b', 'c']

    def test_passes_when_columns_match_exactly(self):
        """Test passes when columns match expected exactly and in order."""
        df = pd.DataFrame(columns=['a', 'b', 'c'])
        check = ExactColumnsCheck(expected_columns=self.expected)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_missing_columns(self):
        """Test fails when expected columns are missing."""
        df = pd.DataFrame(columns=['a', 'b'])
        check = ExactColumnsCheck(expected_columns=self.expected)
        result = check.validate(df)
        self.assertIn("Missing column(s): ['c'].", result['messages'])
        self.assertNotIn("Unexpected column(s", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())

    def test_extra_columns(self):
        """Test fails when unexpected columns are present."""
        df = pd.DataFrame(columns=['a', 'b', 'c', 'd'])
        check = ExactColumnsCheck(expected_columns=self.expected)
        result = check.validate(df)
        self.assertIn("Unexpected column(s): ['d'].", result['messages'])
        self.assertEqual(result['failing_indices'], set())

    def test_missing_and_extra_columns(self):
        """Test fails when both missing and unexpected columns exist."""
        df = pd.DataFrame(columns=['a', 'x'])
        check = ExactColumnsCheck(expected_columns=self.expected)
        result = check.validate(df)
        self.assertIn("Missing column(s): ['b', 'c'].", result['messages'])
        self.assertIn("Unexpected column(s): ['x'].", result['messages'])
        self.assertEqual(result['failing_indices'], set())

    def test_order_mismatch_only(self):
        """Test fails when column order does not match expected."""
        df = pd.DataFrame(columns=['b', 'a', 'c'])
        check = ExactColumnsCheck(expected_columns=self.expected)
        result = check.validate(df)
        self.assertEqual(
            result['messages'],
            ["Column order mismatch: expected ['a', 'b', 'c'], but got ['b', 'a', 'c']."]
        )
        self.assertEqual(result['failing_indices'], set())

        
class TestNoNullsCheck(unittest.TestCase):
    """
    Test suite for NoNullsCheck, verifying detection of null values
    across all or specific columns in a DataFrame.
    """
    def setUp(self):
        """Create a sample DataFrame with nulls in multiple columns."""
        self.df = pd.DataFrame({
            'a': [1, 2, None],
            'b': ['x', 'y', 'z'],
            'c': [None, None, 3]
        })

    def test_default_all_columns(self):
        """Test detection of nulls across all columns by default."""
        check = NoNullsCheck()
        result = check.validate(self.df)
        self.assertIn("Column 'a' contains null values.", result['messages'])
        self.assertIn("Column 'c' contains null values.", result['messages'])
        self.assertEqual(result['failing_indices'], {0, 1, 2})

    def test_specified_columns(self):
        """Test detection of nulls in specified column only."""
        check = NoNullsCheck(columns=['a'])
        result = check.validate(self.df)
        self.assertEqual(len(result['messages']), 1)
        self.assertIn("Column 'a' contains null values.", result['messages'])
        self.assertEqual(result['failing_indices'], {2})

    def test_no_nulls(self):
        """Test passes when DataFrame contains no null values."""
        clean_df = pd.DataFrame({'x': [1, 2], 'y': ['a', 'b']})
        check = NoNullsCheck()
        result = check.validate(clean_df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())



class TestIsEmptyCheck(unittest.TestCase):
    """
    Test suite for IsEmptyCheck, ensuring validation logic detects
    whether a DataFrame is empty as expected.
    """
    def test_passes_if_empty(self):
        """Test passes when DataFrame is empty."""
        df = pd.DataFrame()
        check = IsEmptyCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_if_not_empty(self):
        """Test fails when DataFrame is not empty."""
        df = pd.DataFrame({'a': [1]})
        check = IsEmptyCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('DataFrame is unexpectedly non-empty.', result['messages'][0])
        self.assertEqual(result['failing_indices'], set())



class TestNotEmptyCheck(unittest.TestCase):
    """
    Test suite for NotEmptyCheck, validating that a DataFrame
    is not empty when required.
    """
    def test_passes_if_not_empty(self):
        """Test passes when DataFrame contains rows."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = NotEmptyCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_if_empty(self):
        """Test fails when DataFrame is empty."""
        df = pd.DataFrame()
        check = NotEmptyCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('DataFrame is unexpectedly empty.', result['messages'][0])
        self.assertEqual(result['failing_indices'], set())



class TestRowCountCheck(unittest.TestCase):
    """
    Test suite for RowCountCheck, validating row count constraints including
    exact matches, minimum, and maximum thresholds.
    """
    def test_exact_passes(self):
        """Test passes when row count matches exact constraint."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = RowCountCheck(exact=3)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_exact_fails(self):
        """Test fails when row count does not match exact constraint."""
        df = pd.DataFrame({'a': [1, 2, 3, 4]})
        check = RowCountCheck(exact=3)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("exactly 3", result['messages'][0])

    def test_min_passes(self):
        """Test passes when row count meets minimum threshold."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = RowCountCheck(min=2)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])

    def test_min_fails(self):
        """Test fails when row count is below minimum threshold."""
        df = pd.DataFrame({'a': [1]})
        check = RowCountCheck(min=2)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("at least 2", result['messages'][0])

    def test_max_passes(self):
        """Test passes when row count is within maximum threshold."""
        df = pd.DataFrame({'a': [1, 2]})
        check = RowCountCheck(max=3)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])

    def test_max_fails(self):
        """Test fails when row count exceeds maximum threshold."""
        df = pd.DataFrame({'a': [1, 2, 3, 4]})
        check = RowCountCheck(max=3)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("at most 3", result['messages'][0])

    def test_invalid_usage(self):
        """Test raises ValueError when both exact and min/max are provided."""
        with self.assertRaises(ValueError):
            RowCountCheck(exact=3, min=1)


class TestUniquenessCheck(unittest.TestCase):
    """
    Test suite for UniquenessCheck, validating that rows or subsets of columns
    contain only unique combinations and handling missing column scenarios.
    """
    def test_fails_on_duplicate_rows(self):
        """Test fails when duplicate rows are present in the DataFrame."""
        df = pd.DataFrame({'a': [1, 1], 'b': [2, 2]})
        check = UniquenessCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("duplicate rows", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_passes_on_unique_rows(self):
        """Test passes when all rows in the DataFrame are unique."""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        check = UniquenessCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_column_subset_unique_passes(self):
        """Test passes when specified column subset is unique."""
        df = pd.DataFrame({'x': [1, 1], 'y': [2, 3]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_column_subset_unique_fails(self):
        """Test fails when duplicates exist within specified column subset."""
        df = pd.DataFrame({'x': [1, 1], 'y': [2, 2]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('not unique based on columns', result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_missing_columns_handled(self):
        """Test fails gracefully when specified uniqueness columns are missing."""
        df = pd.DataFrame({'x': [1, 2]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("Missing columns", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())


if __name__ == '__main__':
    unittest.main()

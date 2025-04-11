import unittest
import pandas as pd
from src.dataframe_checks import (
    DefinedColumnsOnlyCheck, 
    IsEmptyCheck,
    NoNullsCheck,
    NotEmptyCheck,
    RowCountCheck,
    UniquenessCheck
)

class TestDefinedColumnsOnlyCheck(unittest.TestCase):
    def test_passes_when_no_extra_columns(self):
        df = pd.DataFrame({'a': [1], 'b': [2]})
        check = DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_when_extra_columns_present(self):
        df = pd.DataFrame({'a': [1], 'b': [2], 'extra': [3]})
        check = DefinedColumnsOnlyCheck(expected_columns=['a', 'b'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("Unexpected columns", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())


class TestNoNullsCheck(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            'a': [1, 2, None],
            'b': ['x', 'y', 'z'],
            'c': [None, None, 3]
        })

    def test_default_all_columns(self):
        check = NoNullsCheck()
        result = check.validate(self.df)
        self.assertIn("Column 'a' contains null values.", result['messages'])
        self.assertIn("Column 'c' contains null values.", result['messages'])
        self.assertEqual(result['failing_indices'], {0, 1, 2})

    def test_specified_columns(self):
        check = NoNullsCheck(columns=['a'])
        result = check.validate(self.df)
        self.assertEqual(len(result['messages']), 1)
        self.assertIn("Column 'a' contains null values.", result['messages'])
        self.assertEqual(result['failing_indices'], {2})

    def test_no_nulls(self):
        clean_df = pd.DataFrame({'x': [1, 2], 'y': ['a', 'b']})
        check = NoNullsCheck()
        result = check.validate(clean_df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())


class TestIsEmptyCheck(unittest.TestCase):
    def test_passes_if_empty(self):
        df = pd.DataFrame()
        check = IsEmptyCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_if_not_empty(self):
        df = pd.DataFrame({'a': [1]})
        check = IsEmptyCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('DataFrame is unexpectedly non-empty.', result['messages'][0])
        self.assertEqual(result['failing_indices'], set())


class TestNotEmptyCheck(unittest.TestCase):
    def test_passes_if_not_empty(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = NotEmptyCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_fails_if_empty(self):
        df = pd.DataFrame()
        check = NotEmptyCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('DataFrame is unexpectedly empty.', result['messages'][0])
        self.assertEqual(result['failing_indices'], set())


class TestRowCountCheck(unittest.TestCase):
    def test_exact_passes(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = RowCountCheck(exact=3)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_exact_fails(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4]})
        check = RowCountCheck(exact=3)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("exactly 3", result['messages'][0])

    def test_min_passes(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        check = RowCountCheck(min=2)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])

    def test_min_fails(self):
        df = pd.DataFrame({'a': [1]})
        check = RowCountCheck(min=2)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("at least 2", result['messages'][0])

    def test_max_passes(self):
        df = pd.DataFrame({'a': [1, 2]})
        check = RowCountCheck(max=3)
        result = check.validate(df)
        self.assertEqual(result['messages'], [])

    def test_max_fails(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4]})
        check = RowCountCheck(max=3)
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("at most 3", result['messages'][0])

    def test_invalid_usage(self):
        with self.assertRaises(ValueError):
            RowCountCheck(exact=3, min=1)


class TestUniquenessCheck(unittest.TestCase):
    def test_fails_on_duplicate_rows(self):
        df = pd.DataFrame({'a': [1, 1], 'b': [2, 2]})
        check = UniquenessCheck()
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("duplicate rows", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_passes_on_unique_rows(self):
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        check = UniquenessCheck()
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_column_subset_unique_passes(self):
        df = pd.DataFrame({'x': [1, 1], 'y': [2, 3]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_column_subset_unique_fails(self):
        df = pd.DataFrame({'x': [1, 1], 'y': [2, 2]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn('not unique based on columns', result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_missing_columns_handled(self):
        df = pd.DataFrame({'x': [1, 2]})
        check = UniquenessCheck(columns=['y'])
        result = check.validate(df)
        self.assertTrue(result['messages'])
        self.assertIn("Missing columns", result['messages'][0])
        self.assertEqual(result['failing_indices'], set())


if __name__ == '__main__':
    unittest.main()

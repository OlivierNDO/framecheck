import unittest
import pandas as pd
from src.dataframe_checks import (
    DefinedColumnsOnlyCheck, 
    IsEmptyCheck,
    NotEmptyCheck,
    UniquenessCheck
)

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

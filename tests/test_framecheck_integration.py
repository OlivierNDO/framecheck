"""Integration tests for main FrameCheck class"""
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from decimal import Decimal
from framecheck.frame_check import FrameCheck


class TestFrameCheckDataFrameChecks(unittest.TestCase):
    """
    Test suite for FrameCheck integration with DataFrame-level checks,
    including column validations, null constraints, row counts, and uniqueness.
    """
    def test_columns_applies_check_to_multiple_fields(self):
        """Test fails when multiple columns exceed max constraint."""
        df = pd.DataFrame({
            'age': [25, 18, 85.0],
            'score': [32, 50, 75]
        })
        schema = FrameCheck().columns(['age', 'score'], type='float', max=70)
        result = schema.validate(df)

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 2)
        self.assertIn('greater than', result.errors[0])

    def test_empty_check_via_framecheck(self):
        """Test passes when DataFrame is empty and schema expects emptiness."""
        df = pd.DataFrame(columns=['a'])
        schema = FrameCheck().empty()
        result = schema.validate(df)
        self.assertTrue(result.is_valid)

    def test_not_empty_check_via_framecheck(self):
        """Test passes when DataFrame is not empty and schema expects data."""
        df = pd.DataFrame({'a': [1]})
        schema = FrameCheck().not_empty()
        result = schema.validate(df)
        self.assertTrue(result.is_valid)

    def test_not_null_column_fails_on_nulls(self):
        """Test fails when not_null=True and column contains nulls."""
        df = pd.DataFrame({'age': [20, None, 35]})
        schema = FrameCheck().column('age', type='float', not_null=True)
        result = schema.validate(df)
        self.assertFalse(result.is_valid)
        self.assertIn('missing values', result.summary())

    def test_raise_on_error_raises_exception_on_failure(self):
        """Test raises ValueError when raise_on_error is enabled and validation fails."""
        df = pd.DataFrame({'score': [0.5, 1.5]})  # 1.5 > 1.0 should fail
        schema = (
            FrameCheck()
            .column('score', type='float', max=1.0)
            .raise_on_error()
        )
        with self.assertRaises(ValueError) as context:
            schema.validate(df)
        self.assertIn("FrameCheck validation failed", str(context.exception))

    def test_row_count_argument_validation(self):
        """Test raises ValueError when both exact and bounds are provided."""
        with self.assertRaises(ValueError) as context:
            FrameCheck().row_count(5, exact=5)
        self.assertIn("do not also pass", str(context.exception))

        with self.assertRaises(ValueError) as context:
            FrameCheck().row_count(5, min=1)
        self.assertIn("do not also pass", str(context.exception))

        with self.assertRaises(ValueError) as context:
            FrameCheck().row_count(5, max=10)
        self.assertIn("do not also pass", str(context.exception))

    def test_row_count_exact_and_bounds(self):
        """Test exact, min, and max row count validation behavior."""
        df = pd.DataFrame({'a': [1, 2, 3]})

        result_exact_pass = FrameCheck().row_count(3).validate(df)
        self.assertTrue(result_exact_pass.is_valid)

        result_exact_fail = FrameCheck().row_count(2).validate(df)
        self.assertFalse(result_exact_fail.is_valid)
        self.assertIn('exactly 2', result_exact_fail.errors[0])

        result_min_fail = FrameCheck().row_count(min=4).validate(df)
        self.assertFalse(result_min_fail.is_valid)
        self.assertIn('at least 4', result_min_fail.errors[0])

        result_max_fail = FrameCheck().row_count(max=2).validate(df)
        self.assertFalse(result_max_fail.is_valid)
        self.assertIn('at most 2', result_max_fail.errors[0])

    def test_unique_check_via_framecheck(self):
        """Test fails when column is not unique and uniqueness is required."""
        df = pd.DataFrame({'a': [1, 2, 2]})
        schema = FrameCheck().column('a', type='int').unique(columns=['a'])
        result = schema.validate(df)
        self.assertIn('not unique', result.summary().lower())


class TestFrameCheckWithCustomCheck(unittest.TestCase):
    """
    Test suite for FrameCheck with custom row-level checks, validating logical
    conditions that combine multiple columns.
    """
    def test_custom_check_integration(self):
        """Test fails when custom condition is violated on any row."""
        df = pd.DataFrame({
            'model_score': [0.1, 0.95, 0.8],
            'flagged_for_review': [False, False, False]
        })

        schema = (
            FrameCheck()
            .custom_check(
                lambda row: row['model_score'] <= 0.9 or row['flagged_for_review'] is True,
                description="flagged_for_review must be True when model_score > 0.9"
            )
        )

        result = schema.validate(df)
        self.assertFalse(result.is_valid)
        self.assertIn("flagged_for_review must be True", result.summary())
        self.assertEqual(result._failing_row_indices, {1})


class TestMultipleChecksSameColumn(unittest.TestCase):
    """Tests handling of multiple sequential checks applied to the same column."""

    def test_sequential_independent_checks(self):
        """Each check on same column is independently enforced."""
        df = pd.DataFrame({'score': [0.1, 0.3, 0.6]})
        schema = (
            FrameCheck()
            .column('score', type='float', min=0.2)
            .column('score', type='float', max=0.55, warn_only=True)
            
        )
        result = schema.validate(df)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)

    def test_redundant_checks(self):
        """Redundant checks do not conflict or interfere."""
        df = pd.DataFrame({'score': [0.5, 0.7]})
        schema = (
            FrameCheck()
            .column('score', type='float', min=0.0)
            .column('score', type='float', min=0.0)
            
        )
        result = schema.validate(df)
        self.assertTrue(result.is_valid)

    def test_error_then_warn(self):
        """Error and warning-level checks are enforced in order."""
        df = pd.DataFrame({'score': [-1, 0.3, 0.9]})
        schema = (
            FrameCheck()
            .column('score', type='float', min=0.0)
            .column('score', type='float', max=0.8, warn_only=True)
            
        )
        result = schema.validate(df)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)


class TestComplexValidationChains(unittest.TestCase):
    """Validates that complex column-level patterns are supported and handled correctly."""

    def test_equals_with_not_null(self):
        df = pd.DataFrame({'flag': [True, True, None]})
        schema = FrameCheck().column('flag', type='bool', equals=True, not_null=True)
        result = schema.validate(df)
        self.assertFalse(result.is_valid)
        self.assertIn('missing values', result.summary())
        self.assertNotIn('must equal', result.summary())

    def test_in_set_then_regex(self):
        """in_set check followed by regex is applied correctly."""
        df = pd.DataFrame({'email': ['a@example.com', 'bademail', 'x@x.com']})
        schema = (
            FrameCheck()
            .column('email', type='string', in_set=['a@example.com', 'x@x.com'])
            .column('email', type='string', regex=r'.+@.+\\..+')
            
        )
        result = schema.validate(df)
        self.assertEqual(len(result.errors), 2)
        
    def test_string_not_in_set_disallowed_values(self):
        df = pd.DataFrame({'color': ['red', 'green', 'blue']})
        schema = FrameCheck().column('color', type='string', not_in_set=['green'])
        result = schema.validate(df)
        self.assertFalse(result.is_valid)
        self.assertIn('disallowed values', result.summary())


class TestGeneralFrameCheckBehavior(unittest.TestCase):
    """Covers general validation behavior and configuration handling."""
    
    def test_column_after_finalize_raises(self):
        """Calling column after only_defined_columns raises error."""
        fc = FrameCheck().only_defined_columns()
        with self.assertRaises(RuntimeError):
            fc.column('x')
            
    def test_equals_and_in_set_raises_value_error(self):
        with self.assertRaises(ValueError):
            FrameCheck().column('x', type='int', equals=5, in_set=[1, 2, 3])
    
    def test_missing_column_with_exists_check(self):
        """Missing column produces friendly message."""
        df = pd.DataFrame({'a': [1]})
        schema = FrameCheck().column('b')
        result = schema.validate(df)
        self.assertIn("'b'", result.summary())

    def test_only_defined_columns_blocks_extra(self):
        """Extra columns raise an error when only_defined_columns is set."""
        df = pd.DataFrame({'a': [1], 'b': [2]})
        schema = (
            FrameCheck()
            .column('a', type='int')
            .only_defined_columns()
            
        )
        result = schema.validate(df)
        self.assertIn('Unexpected columns', result.summary())

    def test_valid_multi_column_schema(self):
        """Multiple valid checks across columns yield no errors."""
        df = pd.DataFrame({
            'a': [1, 2],
            'b': [0.1, 0.9],
            'c': ['x', 'y']
        })
        schema = (
            FrameCheck()
            .column('a', type='int')
            .column('b', type='float')
            .column('c', type='string')
            
        )
        result = schema.validate(df)
        self.assertTrue(result.is_valid)
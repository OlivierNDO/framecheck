"""Unit tests for column_checks.py"""
import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from decimal import Decimal

from framecheck.column_checks import (
    IntColumnCheck,
    FloatColumnCheck,
    StringColumnCheck,
    BoolColumnCheck,
    DatetimeColumnCheck,
    ColumnExistsCheck,
    ColumnCheck
)



class TestColumnCheck(unittest.TestCase):

    def test_validate_raises_not_implemented(self):
        """Raises NotImplementedError when .validate() is called on the abstract base class ColumnCheck"""
        check = ColumnCheck('any_column')
        with self.assertRaises(NotImplementedError):
            check.validate(pd.Series([1, 2, 3]))


class TestBoolColumnCheck(unittest.TestCase):
    """
    Test suite for BoolColumnCheck, validating enforcement of boolean values,
    equality constraints, null handling, and type strictness within a Series.
    """
    def test_all_invalid_values(self):
        """Test fails when all values are non-boolean types."""
        series = pd.Series(['yes', 'no', 1, 0])
        check = BoolColumnCheck('subscribed')
        result = check.validate(series)
        self.assertTrue(result['failing_indices'])
        self.assertEqual(len(result['failing_indices']), 4)

    def test_all_valid_booleans(self):
        """Test passes when all values are valid booleans."""
        series = pd.Series([True, False, True])
        check = BoolColumnCheck('subscribed')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())
        
    def test_equals(self):
        """Test fails when values do not match the equals constraint."""
        series = pd.Series([True, False, True])
        check = BoolColumnCheck('flag', equals=True)
        result = check.validate(series)
        self.assertTrue(any("must equal" in msg for msg in result['messages']))
        self.assertIn(1, result['failing_indices'])
    
    def test_equals_invalid_type(self):
        """Test raises ValueError when equals constraint is not a boolean."""
        with self.assertRaises(ValueError):
            BoolColumnCheck('flag', equals="yes")
            
    def test_ignores_nan_values(self):
        """Test passes when NaN values are present but not_null is False."""
        series = pd.Series([True, None, False, pd.NA, float('nan')])
        check = BoolColumnCheck('subscribed')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())
            
    def test_not_null_flag(self):
        """Test fails when not_null=True and missing values are present."""
        series = pd.Series([True, None, False])
        check = BoolColumnCheck('subscribed', not_null=True)
        result = check.validate(series)
        self.assertTrue(any("missing values" in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_with_non_boolean_values(self):
        """Test fails when non-boolean values are included in Series."""
        series = pd.Series([True, 'yes', 0, False])
        check = BoolColumnCheck('subscribed')
        result = check.validate(series)
        self.assertEqual(len(result['messages']), 1)
        self.assertIn(1, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])


class TestDatetimeColumnCheck(unittest.TestCase):
    """
    Test suite for DatetimeColumnCheck, covering bounds validation (min, max, before, after),
    format enforcement, equality checks, null constraints, and error handling for bad inputs.
    """
    def setUp(self):
        """Set the column name used in all datetime checks."""
        self.col = 'created_at'

    def test_after_bound(self):
        """Test fails when date is before 'today' and after='today' is set."""
        past = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        data = pd.Series([past])
        check = DatetimeColumnCheck(self.col, after='today')
        result = check.validate(data)
        self.assertTrue(any('after' in m for m in result['messages']))
        self.assertIn(0, result['failing_indices'])

    def test_before_after_with_datetime_objects(self):
        """Test fails when values are outside explicit datetime before/after bounds."""
        now = datetime.now()
        early = now - timedelta(days=10)
        late = now + timedelta(days=10)
        data = pd.Series([early, now, late])
        check = DatetimeColumnCheck(self.col, before=now, after=now)
        result = check.validate(data)
        self.assertIn(0, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_before_bound(self):
        """Test fails when date is after 'today' and before='today' is set."""
        future = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        data = pd.Series([future])
        check = DatetimeColumnCheck(self.col, before='today')
        result = check.validate(data)
        self.assertTrue(any('before' in m for m in result['messages']))
        self.assertIn(0, result['failing_indices'])

    def test_equals_invalid_datetime(self):
        """Test fails when values do not match equals constraint or are invalid dates."""
        series = pd.Series(['2024-01-01', '2024-01-02', 'invalid'])
        check = DatetimeColumnCheck(self.col, equals='2024-01-01')
        result = check.validate(series)
        self.assertTrue(any("must equal" in msg for msg in result['messages']))
        self.assertIn(1, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_equals_valid_datetime(self):
        """Test passes when all values equal the specified datetime."""
        series = pd.Series(['2024-01-01', '2024-01-01'])
        check = DatetimeColumnCheck(self.col, equals='2024-01-01')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_equals_with_conflicting_bounds_raises(self):
        """Test raises ValueError when equals is combined with min or max."""
        with self.assertRaises(ValueError):
            DatetimeColumnCheck(self.col, equals='2024-01-01', min='2023-01-01')

    def test_format_enforced_correctly(self):
        """Test passes when datetime strings match specified format."""
        data = pd.Series(['01-04-2024', '02-04-2024'])
        check = DatetimeColumnCheck(self.col, format='%d-%m-%Y')
        result = check.validate(data)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_format_enforced_invalid(self):
        """Test fails when a value doesn't match the specified datetime format."""
        data = pd.Series(['01-04-2024', 'bad-date'])
        check = DatetimeColumnCheck(self.col, format='%d-%m-%Y')
        result = check.validate(data)
        self.assertTrue(result['messages'])
        self.assertIn(1, result['failing_indices'])

    def test_format_parses_bounds(self):
        """Test datetime bound is correctly parsed using the given format."""
        check = DatetimeColumnCheck(self.col, before='04-01-2024', format='%d-%m-%Y')
        self.assertEqual(check.before, datetime(2024, 1, 4))

    def test_inconsistent_type_warning(self):
        """Test warning is returned when mixed datetime types are used."""
        series = pd.Series(['2024-01-01', pd.Timestamp('2024-01-02')])
        check = DatetimeColumnCheck(self.col)
        result = check.validate(series)
        self.assertTrue(any('inconsistent datetime types' in m.lower() for m in result['messages']))

    def test_invalid_bound_format_error(self):
        """Test raises ValueError when bound cannot be parsed using format."""
        with self.assertRaises(ValueError):
            DatetimeColumnCheck(self.col, before='04-01-2024', format='%Y/%m/%d')

    def test_invalid_bound_format_raises_value_error(self):
        """Test raises ValueError for mismatched bound format."""
        with self.assertRaises(ValueError):
            DatetimeColumnCheck(self.col, before='04-01-2024', format='%Y/%m/%d')

    def test_invalid_coercion_flagged(self):
        """Test fails when non-date strings cannot be coerced to datetime."""
        series = pd.Series(['2024-01-01', 'bad-date'])
        check = DatetimeColumnCheck(self.col, format='%Y-%m-%d')
        result = check.validate(series)
        self.assertTrue(result['messages'])
        self.assertIn(1, result['failing_indices'])

    def test_invalid_strings_fail(self):
        """Test fails when non-date strings are present."""
        data = pd.Series(['2024-01-01', 'notadate', ''])
        check = DatetimeColumnCheck(self.col)
        result = check.validate(data)
        self.assertTrue(result['messages'])
        self.assertIn(1, result['failing_indices'])

    def test_max_bound(self):
        """Test fails when value exceeds max bound."""
        data = pd.Series(['2024-01-01', '2025-01-01'])
        check = DatetimeColumnCheck(self.col, max='2024-12-31')
        result = check.validate(data)
        self.assertTrue(any('max' in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_min_bound(self):
        """Test fails when value is below min bound."""
        data = pd.Series(['2024-01-01', '2023-01-01'])
        check = DatetimeColumnCheck(self.col, min='2024-01-01')
        result = check.validate(data)
        self.assertTrue(any('min' in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_not_null_flag(self):
        """Test fails when not_null=True and null values are present."""
        series = pd.Series(['2024-01-01', None, '2024-01-02'])
        check = DatetimeColumnCheck(self.col, not_null=True)
        result = check.validate(series)
        self.assertTrue(any("missing values" in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_now_bound(self):
        """Test fails when date is after now and before='now' is used."""
        data = pd.Series([(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')])
        check = DatetimeColumnCheck(self.col, before='now')
        result = check.validate(data)
        self.assertTrue(any('before' in m for m in result['messages']))

    def test_string_tomorrow_bound(self):
        """Test parses 'tomorrow' correctly as before bound."""
        check = DatetimeColumnCheck(self.col, before='tomorrow')
        self.assertIsNotNone(check.before)

    def test_string_yesterday_bound(self):
        """Test parses 'yesterday' correctly as after bound."""
        check = DatetimeColumnCheck(self.col, after='yesterday')
        self.assertIsNotNone(check.after)

    def test_tomorrow_bound(self):
        """Test passes when value is before tomorrow."""
        tomorrow = datetime.today() + timedelta(days=1)
        date_str = tomorrow.strftime('%Y-%m-%d')
        check = DatetimeColumnCheck(self.col, before=tomorrow)
        data = pd.Series([date_str])
        result = check.validate(data)
        self.assertEqual(result['messages'], [])

    def test_uncoercible_date_format_raises_value_error(self):
        """Test raises ValueError when bound can't be coerced using format."""
        with self.assertRaises(ValueError):
            DatetimeColumnCheck(self.col, before='04-01-2024', format='%Y/%m/%d')

    def test_valid_dates_pass(self):
        """Test passes when all values are valid dates within bounds."""
        data = pd.Series(['2024-01-01', '2024-04-01', '2025-01-01'])
        check = DatetimeColumnCheck(self.col)
        result = check.validate(data)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_yesterday_bound(self):
        """Test passes when value is after yesterday and after=yesterday is set."""
        yesterday = (datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        date_str = yesterday.strftime('%Y-%m-%d')
        check = DatetimeColumnCheck(self.col, after=yesterday)
        data = pd.Series([date_str])
        result = check.validate(data)
        self.assertEqual(result['messages'], [])


class TestFloatColumnCheck(unittest.TestCase):
    """
    Test suite for FloatColumnCheck, validating numeric enforcement,
    range constraints, allowed/disallowed sets, equality, and null handling.
    """
    def test_all_invalid_types_skips_range_and_inf_checks(self):
        """Test fails when all values are non-numeric and skips range/infinity checks."""
        series = pd.Series(['a', 'b', 'c'])
        check = FloatColumnCheck('score')
        result = check.validate(series)
        self.assertTrue(any('not numeric' in m for m in result['messages']))
        self.assertEqual(len(result['failing_indices']), 3)

    def test_both_min_and_max(self):
        """Test fails when values fall outside specified min and max bounds."""
        series = pd.Series([-1, 0.5, 2])
        check = FloatColumnCheck('score', min=0.0, max=1.0)
        result = check.validate(series)
        self.assertEqual(len(result['messages']), 2)
        self.assertIn(0, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_equals_valid_float(self):
        """Test passes when all values exactly match the specified float."""
        series = pd.Series([3.14, 3.14, 3.14])
        check = FloatColumnCheck('score', equals=3.14)
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_equals_invalid_float(self):
        """Test fails when values do not match the specified float."""
        series = pd.Series([3.14, 2.71, 1.61])
        check = FloatColumnCheck('score', equals=3.14)
        result = check.validate(series)
        self.assertTrue(any("must equal" in msg for msg in result['messages']))
        self.assertEqual(result['failing_indices'], {1, 2})

    def test_in_set_constraint(self):
        """Test fails when values fall outside the allowed set."""
        series = pd.Series([0.1, 0.2, 0.3, 0.5])
        check = FloatColumnCheck('score', in_set=[0.1, 0.2])
        result = check.validate(series)
        self.assertIn("contains unexpected values", result['messages'][0])
        self.assertEqual(result['failing_indices'], {2, 3})

    def test_infinite_values_trigger_warning(self):
        """Test fails and warns when infinite values are present."""
        series = pd.Series([1.0, np.inf, 2.0, -np.inf])
        check = FloatColumnCheck('score')
        result = check.validate(series)
        self.assertTrue(any('infinite values' in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])
        self.assertIn(3, result['failing_indices'])

    def test_invalid_types(self):
        """Test fails when series contains non-numeric types."""
        series = pd.Series([1.0, 'bad', None])
        check = FloatColumnCheck('score')
        result = check.validate(series)
        self.assertTrue(any("not numeric" in msg for msg in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_min_constraint(self):
        """Test fails when values are below the specified min."""
        series = pd.Series([0.5, -0.1, 1.0])
        check = FloatColumnCheck('score', min=0.0)
        result = check.validate(series)
        self.assertIn("less than 0.0", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_max_constraint(self):
        """Test fails when values exceed the specified max."""
        series = pd.Series([0.3, 0.9, 1.1])
        check = FloatColumnCheck('score', max=1.0)
        result = check.validate(series)
        self.assertIn("greater than 1.0", result['messages'][0])
        self.assertIn(2, result['failing_indices'])

    def test_nan_values_are_ignored(self):
        """Test passes when NaNs are present but otherwise within bounds."""
        series = pd.Series([0.1, np.nan, 0.8])
        check = FloatColumnCheck('score', min=0.0, max=1.0)
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_not_in_set_constraint(self):
        """Test fails when disallowed values are present in the series."""
        series = pd.Series([0.1, 0.2, 0.3, 0.5, np.nan])
        check = FloatColumnCheck('score', not_in_set=[0.3, 0.5])
        result = check.validate(series)
        self.assertIn("contains disallowed values", result['messages'][0])
        self.assertEqual(result['failing_indices'], {2, 3})

    def test_not_null_flag(self):
        """Test fails when not_null=True and null values are present."""
        series = pd.Series([1.0, np.nan, 2.0])
        check = FloatColumnCheck('score', not_null=True)
        result = check.validate(series)
        self.assertTrue(any("missing values" in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_valid_floats(self):
        """Test passes when all values are valid floats."""
        series = pd.Series([0.1, 0.5, 0.99])
        check = FloatColumnCheck('score')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_valid_ints_and_decimals(self):
        """Test passes when values include ints and Decimals convertible to float."""
        series = pd.Series([1, 2.5, Decimal('3.3')])
        check = FloatColumnCheck('score')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())


class TestIntColumnCheck(unittest.TestCase):
    """
    Test suite for IntColumnCheck, validating integer type enforcement,
    range checks, value set constraints, null handling, and type exclusions.
    """
    def test_booleans_are_excluded(self):
        """Test fails when boolean values are treated as integers."""
        series = pd.Series([1, True, False])
        check = IntColumnCheck('col')
        result = check.validate(series)
        self.assertEqual(len(result['messages']), 1)
        self.assertIn(1, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_equals_valid_integer(self):
        """Test passes when all values equal the specified integer."""
        series = pd.Series([42, 42, 42])
        check = IntColumnCheck('col', equals=42)
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_equals_invalid_integer(self):
        """Test fails when some values do not match the specified integer."""
        series = pd.Series([42, 99, 13])
        check = IntColumnCheck('col', equals=42)
        result = check.validate(series)
        self.assertTrue(any("must equal" in msg for msg in result['messages']))
        self.assertEqual(result['failing_indices'], {1, 2})

    def test_equals_with_non_integer_value_raises(self):
        """Test raises ValueError when equals is not an integer."""
        with self.assertRaises(ValueError) as context:
            IntColumnCheck('col', equals='forty-two')
        self.assertIn("must be an integer", str(context.exception))

    def test_in_set_constraint(self):
        """Test fails when values fall outside allowed set."""
        series = pd.Series([1, 2, 3, 4])
        check = IntColumnCheck('col', in_set=[1, 2])
        result = check.validate(series)
        self.assertIn("contains unexpected values", result['messages'][0])
        self.assertEqual(result['failing_indices'], {2, 3})

    def test_infinite_values_in_int_column(self):
        """Test fails when infinite values are included."""
        series = pd.Series([1.0, float('inf'), float('-inf')])
        check = IntColumnCheck('col')
        result = check.validate(series)
        self.assertTrue(any('infinite values' in m.lower() for m in result['messages']))
        self.assertIn(1, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_integer_like_floats_are_accepted(self):
        """Test passes when float values are integer-like (e.g., 1.0)."""
        series = pd.Series([1.0, 2.0, 3.0])
        check = IntColumnCheck('col')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_nan_values_are_ignored(self):
        """Test passes when NaNs are present but otherwise valid."""
        series = pd.Series([1, np.nan, 10.0])
        check = IntColumnCheck('col', min=0, max=100)
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_non_integer_values_flagged(self):
        """Test fails when values are not integer-like (floats or strings)."""
        series = pd.Series([1.1, 2.5, 'a'])
        check = IntColumnCheck('col')
        result = check.validate(series)
        self.assertEqual(len(result['messages']), 1)
        self.assertIn(1, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_not_in_set_constraint(self):
        """Test fails when disallowed values are present in the series."""
        series = pd.Series([1, 2, 3, 4, np.nan])
        check = IntColumnCheck('col', not_in_set=[3, 4])
        result = check.validate(series)
        self.assertIn("contains disallowed values", result['messages'][0])
        self.assertEqual(result['failing_indices'], {2, 3})

    def test_not_null_flag(self):
        """Test fails when not_null=True and null values are present."""
        series = pd.Series([1, np.nan, 42])
        check = IntColumnCheck('col', not_null=True)
        result = check.validate(series)
        self.assertTrue(any("missing values" in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_range_check_both_min_and_max(self):
        """Test fails when values fall outside specified min and max."""
        series = pd.Series([1, 10, 30])
        check = IntColumnCheck('col', min=5, max=25)
        result = check.validate(series)
        self.assertEqual(len(result['messages']), 2)
        self.assertIn(0, result['failing_indices'])
        self.assertIn(2, result['failing_indices'])

    def test_range_check_max(self):
        """Test fails when values exceed the specified max."""
        series = pd.Series([10, 25, 20])
        check = IntColumnCheck('col', max=20)
        result = check.validate(series)
        self.assertIn("greater than 20", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_range_check_min(self):
        """Test fails when values are below the specified min."""
        series = pd.Series([10, 5, 20])
        check = IntColumnCheck('col', min=6)
        result = check.validate(series)
        self.assertIn("less than 6", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_valid_integer_values(self):
        """Test passes when all values are valid integers."""
        series = pd.Series([1, 2, 3])
        check = IntColumnCheck('col')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())


class TestStringColumnCheck(unittest.TestCase):
    """
    Test suite for StringColumnCheck, validating regex matching,
    value set constraints, null handling, and type coercion.
    """
    def test_both_regex_and_in_set(self):
        """Test fails when values violate both regex and in_set constraints."""
        series = pd.Series(['apple', 'banana', 'bad!', 'not_fruit'])
        check = StringColumnCheck('fruit', regex=r'^[a-z]+$', in_set=['apple', 'banana', 'cherry'])
        result = check.validate(series)
        self.assertEqual(result['failing_indices'], {2, 3})
        self.assertEqual(len(result['messages']), 2)

    def test_empty_series(self):
        """Test passes when input Series is empty."""
        series = pd.Series([], dtype=object)
        check = StringColumnCheck('anything', regex=r'.*')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_equals_invalid_value(self):
        """Test fails when not all values match the specified string."""
        series = pd.Series(['yes', 'no', 'yes'])
        check = StringColumnCheck('status', equals='yes')
        result = check.validate(series)
        self.assertIn("must equal", result['messages'][0])
        self.assertIn(1, result['failing_indices'])

    def test_equals_valid_value(self):
        """Test passes when all values match the specified string."""
        series = pd.Series(['yes', 'yes', 'yes'])
        check = StringColumnCheck('status', equals='yes')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_in_set_invalid(self):
        """Test fails when values outside the allowed set are present."""
        series = pd.Series(['red', 'yellow', 'blue'])
        check = StringColumnCheck('color', in_set=['red', 'green', 'blue'])
        result = check.validate(series)
        self.assertIn("color", result['messages'][0])
        self.assertEqual(result['failing_indices'], {1})

    def test_in_set_valid(self):
        """Test passes when all values are within the allowed set."""
        series = pd.Series(['red', 'green', 'blue'])
        check = StringColumnCheck('color', in_set=['red', 'green', 'blue'])
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_in_set_with_nulls(self):
        """Test passes when values are in set or null."""
        series = pd.Series(['red', None, 'blue', np.nan])
        check = StringColumnCheck('color', in_set=['red', 'blue'])
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_non_string_values_are_coerced(self):
        """Test fails when coerced values don't match regex."""
        series = pd.Series(['abc', 123, True])
        check = StringColumnCheck('mixed', regex=r'^[a-z]+$')
        result = check.validate(series)
        self.assertEqual(result['failing_indices'], {1, 2})

    def test_not_null_flag(self):
        """Test fails when nulls are present and not_null=True."""
        series = pd.Series(['a', None, 'b'])
        check = StringColumnCheck('str_col', not_null=True)
        result = check.validate(series)
        self.assertTrue(any("missing values" in m for m in result['messages']))
        self.assertIn(1, result['failing_indices'])

    def test_regex_match_all(self):
        """Test passes when all values match the regex pattern."""
        series = pd.Series(['abc@example.com', 'def@site.org'])
        check = StringColumnCheck('email', regex=r'.+@.+\..+')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_regex_match_some_fail(self):
        """Test fails when some values do not match the regex."""
        series = pd.Series(['abc@example.com', 'invalid_email', 'noatsign'])
        check = StringColumnCheck('email', regex=r'.+@.+\..+')
        result = check.validate(series)
        self.assertIn("email", result['messages'][0])
        self.assertEqual(result['failing_indices'], {1, 2})

    def test_regex_with_nulls(self):
        """Test passes when null values are ignored in regex validation."""
        series = pd.Series(['abc@example.com', None, np.nan])
        check = StringColumnCheck('email', regex=r'.+@.+\..+')
        result = check.validate(series)
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['failing_indices'], set())

    def test_repr_and_initialization(self):
        """Test class is initialized and its attributes are correctly set."""
        check = StringColumnCheck('name', regex='^[a-z]+$', in_set=['alice', 'bob'], raise_on_fail=False)
        self.assertEqual(check.column_name, 'name')
        self.assertEqual(check.regex, '^[a-z]+$')
        self.assertEqual(check.in_set, ['alice', 'bob'])
        self.assertFalse(check.raise_on_fail)


if __name__ == '__main__':
    unittest.main()

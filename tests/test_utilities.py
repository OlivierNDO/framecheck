"""Unit tests for utilities.py"""
import unittest
from framecheck.utilities import CheckFactory
from framecheck.column_checks import ColumnCheck


# Simulated checks for testing
class MaxCheck(ColumnCheck):
    """
    Dummy max check used for testing CheckFactory. Always returns success,
    but simulates a max constraint being applied.
    """

    def __init__(self, column_name: str, raise_on_fail: bool = True, max: int = None):
        """
        Initialize MaxCheck with an optional max value.

        Parameters
        ----------
        column_name : str
            The name of the column to check.
        raise_on_fail : bool, optional
            Whether failure should raise an error.
        max : int, optional
            The maximum allowed value (not used in dummy).
        """
        super().__init__(column_name, raise_on_fail)
        self.max = max

    def validate(self, series):
        """
        Dummy validation logic. Always passes.

        Parameters
        ----------
        series : pd.Series
            Column data to validate.

        Returns
        -------
        dict
            A result dict with no messages or failures.
        """
        return {"messages": [], "failing_indices": set()}


class RequiredCheck(ColumnCheck):
    """
    Dummy required field check used in factory test cases.
    Always passes, simulating enforcement of required presence.
    """

    def __init__(self, column_name: str, raise_on_fail: bool = True):
        """
        Initialize RequiredCheck.

        Parameters
        ----------
        column_name : str
            The name of the column to check.
        raise_on_fail : bool, optional
            Whether failure should raise an error.
        """
        super().__init__(column_name, raise_on_fail)

    def validate(self, series):
        """
        Dummy validation logic. Always passes.

        Parameters
        ----------
        series : pd.Series
            Column data to validate.

        Returns
        -------
        dict
            A result dict with no messages or failures.
        """
        return {"messages": [], "failing_indices": set()}


# Register the custom check types for this test
CheckFactory.register("max_check")(MaxCheck)
CheckFactory.register("required")(RequiredCheck)


class TestCheckFactory(unittest.TestCase):
    """
    Test suite for CheckFactory, verifying check instantiation,
    error handling for unknown types, and validation of keyword arguments.
    """
    def test_multiple_check_creation_from_kwargs(self):
        """Test factory creates multiple checks based on flags in kwargs."""
        checks = CheckFactory.create(
            'max_check',
            column_name='score',
            raise_on_fail=True,
            max=100,
            required=True  # Triggers a second check instance
        )

        self.assertIsInstance(checks, list)
        self.assertEqual(len(checks), 2)

        check_types = {type(c) for c in checks}
        self.assertIn(MaxCheck, check_types)
        self.assertIn(RequiredCheck, check_types)

    def test_raises_on_unknown_check_type(self):
        """Test raises ValueError for unregistered check type."""
        with self.assertRaises(ValueError) as context:
            CheckFactory.create(
                'nonexistent_check',
                column_name='score',
                raise_on_fail=True
            )
        self.assertIn("Unknown column type", str(context.exception))

    def test_raises_on_invalid_kwargs(self):
        """Test raises ValueError when unexpected kwargs are passed."""
        with self.assertRaises(ValueError) as context:
            CheckFactory.create(
                'max_check',
                column_name='score',
                raise_on_fail=True,
                invalid_kwarg=True
            )
        self.assertIn("Invalid keyword arguments", str(context.exception))

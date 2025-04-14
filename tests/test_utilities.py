import unittest
from framecheck.utilities import CheckFactory
from framecheck.column_checks import ColumnCheck


# Simulated checks for testing
class MaxCheck(ColumnCheck):
    def __init__(self, column_name: str, raise_on_fail: bool = True, max: int = None):
        super().__init__(column_name, raise_on_fail)
        self.max = max

    def validate(self, series):
        return {"messages": [], "failing_indices": set()}


class RequiredCheck(ColumnCheck):
    def __init__(self, column_name: str, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)

    def validate(self, series):
        return {"messages": [], "failing_indices": set()}


# Register the custom check types for this test
CheckFactory.register("max_check")(MaxCheck)
CheckFactory.register("required")(RequiredCheck)


class TestCheckFactory(unittest.TestCase):

    def test_multiple_check_creation_from_kwargs(self):
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
        with self.assertRaises(ValueError) as context:
            CheckFactory.create(
                'nonexistent_check',
                column_name='score',
                raise_on_fail=True
            )
        self.assertIn("Unknown column type", str(context.exception))

    def test_raises_on_invalid_kwargs(self):
        with self.assertRaises(ValueError) as context:
            CheckFactory.create(
                'max_check',
                column_name='score',
                raise_on_fail=True,
                invalid_kwarg=True
            )
        self.assertIn("Invalid keyword arguments", str(context.exception))


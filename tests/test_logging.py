"""Tests for FrameCheck's logger integration"""
import unittest
from unittest.mock import Mock, patch
import warnings
import pandas as pd
import logging
from framecheck.frame_check import FrameCheck, FrameCheckWarning


class TestFrameCheckLogging(unittest.TestCase):
    """
    Test suite for FrameCheck's logger integration, validating proper message routing
    to either the provided logger or the warnings system.
    """
    def setUp(self):
        """Set up test data and mocks."""
        self.df = pd.DataFrame({
            'age': [25, 18, 85],
            'score': [32, 50, 75]
        })
        # Create a mock logger for testing
        self.mock_logger = Mock(spec=logging.Logger)

    def test_logger_integration_basic(self):
        """Test that logger is properly stored in the FrameCheck instance."""
        schema = FrameCheck(logger=self.mock_logger)
        self.assertEqual(schema._logger, self.mock_logger)

    def test_errors_sent_to_logger(self):
        """Test that validation errors are sent to the logger's error method."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('age', type='int', max=50)  # Will fail on 85
        
        result = schema.validate(self.df)
        
        self.assertFalse(result.is_valid)
        self.mock_logger.error.assert_called_once()
        # Check message content
        call_args = self.mock_logger.error.call_args[0][0]
        self.assertIn("FrameCheck validation errors", call_args)
        self.assertIn("'age' has values greater than 50", call_args)

    def test_warnings_sent_to_logger(self):
        """Test that validation warnings are sent to the logger's warning method."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('age', type='int', max=50, warn_only=True)  # Will warn on 85
        
        result = schema.validate(self.df)
        
        self.assertTrue(result.is_valid)  # warn_only=True means this is valid
        self.mock_logger.warning.assert_called_once()
        # Check message content
        call_args = self.mock_logger.warning.call_args[0][0]
        self.assertIn("FrameCheck validation warnings", call_args)
        self.assertIn("'age' has values greater than 50", call_args)

    def test_both_errors_and_warnings_logged(self):
        """Test both error and warning messages are properly logged."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('age', type='int', max=50)  # Error on 85
        schema.column('score', type='int', min=40, warn_only=True)  # Warning on 32
        
        result = schema.validate(self.df)
        
        self.assertFalse(result.is_valid)
        self.mock_logger.error.assert_called_once()
        self.mock_logger.warning.assert_called_once()
        
        # Check error message
        error_msg = self.mock_logger.error.call_args[0][0]
        self.assertIn("'age' has values greater than 50", error_msg)
        
        # Check warning message
        warning_msg = self.mock_logger.warning.call_args[0][0]
        self.assertIn("'score' has values less than 40", warning_msg)

    def test_no_warnings_no_logger_calls(self):
        """Test that no logger calls are made when validation passes."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('age', type='int', min=10, max=100)  # All values pass
        schema.column('score', type='int', min=30, max=80)  # All values pass
        
        result = schema.validate(self.df)
        
        self.assertTrue(result.is_valid)
        self.mock_logger.error.assert_not_called()
        self.mock_logger.warning.assert_not_called()

    def test_backwards_compatibility_no_logger(self):
        """Test warnings are still emitted when no logger is provided."""
        schema = FrameCheck()  # No logger provided
        schema.column('age', type='int', max=50)  # Will fail on 85
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = schema.validate(self.df)
            
            self.assertFalse(result.is_valid)
            self.assertTrue(len(w) > 0)
            self.assertTrue(issubclass(w[0].category, FrameCheckWarning))
            self.assertIn("'age' has values greater than 50", str(w[0].message))

    def test_log_errors_false_no_warnings(self):
        """Test that log_errors=False suppresses warnings but not logger calls."""
        # Test with logger
        schema_with_logger = FrameCheck(log_errors=False, logger=self.mock_logger)
        schema_with_logger.column('age', type='int', max=50)  # Will fail on 85
        
        result = schema_with_logger.validate(self.df)
        
        self.assertFalse(result.is_valid)
        self.mock_logger.error.assert_called_once()  # Logger still gets errors
        
        # Test without logger (should suppress warnings)
        schema_no_logger = FrameCheck(log_errors=False)  # No warnings
        schema_no_logger.column('age', type='int', max=50)  # Would normally warn
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = schema_no_logger.validate(self.df)
            
            self.assertFalse(result.is_valid)
            self.assertEqual(len(w), 0)  # No warnings emitted

    def test_raise_on_error_with_logger(self):
        """Test that raise_on_error works with logger integration."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('age', type='int', max=50).raise_on_error()  # Will fail and raise
        
        with self.assertRaises(ValueError) as context:
            schema.validate(self.df)
            
        self.assertIn("FrameCheck validation failed", str(context.exception))
        self.mock_logger.error.assert_not_called()  # Error is raised, not logged

    def test_missing_column_with_logger(self):
        """Test that missing column errors are properly logged."""
        schema = FrameCheck(logger=self.mock_logger)
        schema.column('nonexistent_column', type='int')
        result = schema.validate(self.df)
        self.assertFalse(result.is_valid)
        self.mock_logger.error.assert_called_once()
        call_args = self.mock_logger.error.call_args[0][0]
        self.assertIn("Column 'nonexistent_column' is missing", call_args)

    def test_empty_validation_messages(self):
        """Test handling of empty validation message lists."""
        schema = FrameCheck(logger=self.mock_logger)
        schema._emit_warnings([])
        schema._emit_errors([])
        self.mock_logger.warning.assert_not_called()
        self.mock_logger.error.assert_not_called()

    def test_emit_warnings_method_directly(self):
        """Test the _emit_warnings method directly to verify warning behavior."""
        schema = FrameCheck()  # No logger
        warning_messages = ["Sample warning message"]
        with patch('warnings.warn') as mock_warn:
            schema._emit_warnings(warning_messages)
            mock_warn.assert_called_once()
            args, kwargs = mock_warn.call_args
            self.assertIn("Sample warning message", args[0])
            if len(args) > 1:
                self.assertEqual(args[1], FrameCheckWarning)
            elif 'category' in kwargs:
                self.assertEqual(kwargs['category'], FrameCheckWarning)
            if 'stacklevel' in kwargs:
                self.assertEqual(kwargs['stacklevel'], 3)



if __name__ == '__main__':
    unittest.main()
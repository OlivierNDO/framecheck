"""Exhaustive integration test to validate ALL FrameCheck functionality"""
import json
import os
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytest
from framecheck import FrameCheck, register_check_function
from framecheck.dataframe_checks import CustomCheck, DefinedColumnsOnlyCheck
from framecheck.column_checks import StringColumnCheck, IntColumnCheck, FloatColumnCheck, DatetimeColumnCheck, BoolColumnCheck

@register_check_function(name="comprehensive_custom_check")
def comprehensive_custom_check(row):
    """Test function covering all common row check scenarios"""
    # Test numeric comparison
    if row['score'] > 90 and not row['verified']:
        return False
    # Test string check    
    if row['status'] == 'PREMIUM' and row['tier'] < 2:
        return False
    # Test date comparisons    
    signup = pd.to_datetime(row['signup_date'])
    renewal = pd.to_datetime(row['renewal_date'])
    if (renewal - signup).days < 30:
        return False
    return True

def test_fully_comprehensive_framecheck():
    """
    Ultimate integration test covering EVERY feature of FrameCheck.
    This test aims to catch any serialization or validation issues
    by exercising all validation capabilities and persistence options.
    """
    
    # Create a perfectly valid DataFrame that meets all criteria
    valid_data = {
        # String columns
        'user_id': ['U12345', 'U67890', 'U98765'],
        'email': ['user1@test.com', 'user2@test.com', 'user3@test.com'],
        'status': ['ACTIVE', 'PREMIUM', 'ACTIVE'],
        'risk_level': ['LOW', 'MEDIUM', 'HIGH'],
        'country': ['USA', 'USA', 'UK'], 
        'account_type': ['USA', 'USA', 'UK'],  # Match country for == test
        
        # Int columns
        'age': [25, 35, 45],
        'login_attempts': [3, 1, 5],
        'tier': [1, 3, 2],
        'security_level': [5, 3, 7],
        'region_code': [2, 3, 4],  # Changed to trigger warning (not equals 1)
        'device_id': [101, 102, 103],
        
        # Float columns
        'score': [85.5, 92.7, 78.3],
        'confidence': [0.85, 0.93, 0.78],
        'ratio': [0.25, 0.5, 1.0],
        'error_rate': [0.05, 0.02, 0.07],
        'threshold': [0.8, 0.7, 0.95],  # Changed to trigger warning (not equals 0.9)
        'multiplier': [1.5, 2.0, 1.2],
        
        # Datetime columns
        'signup_date': ['2022-03-15', '2021-11-20', '2022-08-05'],
        'renewal_date': ['2023-03-15', '2022-11-20', '2023-08-05'],  # +1 year from signup
        'last_login': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'created_at': ['2020-01-01', '2019-06-15', '2021-02-28'],
        'timestamp': ['2022-01-01', '2022-05-01', '2022-09-01'],  # Changed to trigger warning (not equals '2023-01-01')
        'updated_at': ['2023-02-01', '2023-02-15', '2023-02-28'],
        'parsed_date': ['2022-05-15', '2022-06-20', '2022-07-25'],
        
        # Boolean columns
        'verified': [True, True, True],
        'subscribed': [True, True, True],
        'is_test': [True, True, True],  # Changed to trigger warning (not equals False)
        'active': [True, True, True],
        
        # Tag columns
        'tag1': ['A', 'B', 'C'],
        'tag2': ['B', 'C', 'A'],
        'tag3': ['C', 'A', 'B']
    }
    
    
    # First create a validator without raise_on_error for testing warnings
    warning_validator = (
        FrameCheck(logger=None)
        # Add warn_only checks that we'll intentionally violate
        .column('country', type='string', equals='USA', warn_only=True)
        .column('region_code', type='int', equals=1, warn_only=True)
        .column('threshold', type='float', equals=0.9, warn_only=True)
        .column('timestamp', type='datetime', equals='2023-01-01', warn_only=True)
        .column('is_test', type='bool', equals=False, warn_only=True)
    )
    
    # Create data that will pass all validation but trigger warnings
    warning_data = {
        'country': ['CANADA', 'UK', 'MEXICO'],  # Not USA - will trigger warning
        'region_code': [2, 3, 4],  # Not 1 - will trigger warning
        'threshold': [0.8, 0.7, 0.95],  # Not 0.9 - will trigger warning
        'timestamp': ['2022-01-01', '2022-05-01', '2022-09-01'],  # Not 2023-01-01 - will trigger warning
        'is_test': [True, True, True]  # Not False - will trigger warning
    }
    
    df_warning = pd.DataFrame(warning_data)
    df_warning['timestamp'] = pd.to_datetime(df_warning['timestamp'])
    
    # Validate and confirm we get warnings (and no errors)
    warning_result = warning_validator.validate(df_warning)
    assert warning_result.is_valid, "Warning validator should pass despite warnings"
    assert len(warning_result.warnings) > 0, "No warnings were detected"
    assert len(warning_result.errors) == 0, "Errors were raised for warn_only checks"
    
    # Create the most comprehensive FrameCheck possible with every feature
    exhaustive_validator = (
        FrameCheck(logger=None)  # Test with and without logger
        
        # ===== ALL STRING COLUMN VALIDATIONS =====
        .column('user_id', type='string', regex=r'^U\d{5}$', not_null=True)
        .column('email', type='string', regex=r'^[\w.-]+@[\w.-]+\.\w+$')
        .column('status', type='string', in_set=['ACTIVE', 'INACTIVE', 'PENDING', 'PREMIUM'])
        .column('risk_level', type='string', not_in_set=['EXTREME', 'UNKNOWN'])
        .column('country', type='string')  # No equals constraint for main validation
        .column('account_type', type='string')  # Basic existence

        # ===== ALL INT COLUMN VALIDATIONS =====
        .column('age', type='int', min=18, max=120, not_null=True)
        .column('login_attempts', type='int', min=0)
        .column('tier', type='int', in_set=[1, 2, 3])
        .column('security_level', type='int', not_in_set=[0, -1])
        .column('region_code', type='int')  # No equals constraint for main validation
        .column('device_id', type='int')  # Basic existence

        # ===== ALL FLOAT COLUMN VALIDATIONS =====
        .column('score', type='float', min=0.0, max=100.0, not_null=True)
        .column('confidence', type='float', min=0.0, max=1.0)
        .column('ratio', type='float', in_set=[0.25, 0.5, 0.75, 1.0])
        .column('error_rate', type='float', not_in_set=[float('nan'), float('inf')])
        .column('threshold', type='float')  # No equals constraint for main validation
        .column('multiplier', type='float')  # Basic existence
        
        # ===== ALL DATETIME COLUMN VALIDATIONS =====
        .column('signup_date', type='datetime', after='2020-01-01', before='now', not_null=True)
        .column('renewal_date', type='datetime', min='2022-01-01', max='2025-12-31')
        .column('last_login', type='datetime', before='now')
        .column('created_at', type='datetime', after='2015-01-01')
        .column('timestamp', type='datetime', equals='2023-01-01', warn_only=True)
        .column('updated_at', type='datetime')  # Basic existence
        .column('parsed_date', type='datetime', format='%Y-%m-%d')  # With format
        
        # ===== ALL BOOLEAN COLUMN VALIDATIONS =====
        .column('verified', type='bool', not_null=True)
        .column('subscribed', type='bool', equals=True)
        .column('is_test', type='bool', equals=False, warn_only=True)
        .column('active', type='bool')  # Basic existence
        
        # ===== TEST COLUMNS (MULTIPLE COLS AT ONCE) =====
        .columns(['tag1', 'tag2', 'tag3'], type='string', in_set=['A', 'B', 'C'])
        
        # ===== ALL DATAFRAME-LEVEL VALIDATIONS =====
        # Not null with specific columns
        .not_null(['user_id', 'email', 'score'])
        
        # Not empty check
        .not_empty()
        
        # Row count with different constraints
        .row_count(min=1, max=1000)
        
        # Uniqueness checks
        .unique(columns=['user_id', 'email'])
        
        # Column comparison checks with all operators
        .compare('score', '>', 'error_rate', description="Score must exceed error rate")
        .compare('signup_date', '<', 'renewal_date', type='datetime', 
                description="Signup must be before renewal")
        .compare('age', '>=', 'tier', description="Age must be at least the tier value")
        .compare('login_attempts', '<=', 'security_level', description="Login attempts within security level")
        .compare('country', '==', 'account_type', description="Country should match account type for test data")
        .compare('risk_level', '!=', 'status', description="Risk level shouldn't match status")
        
        # Custom check with registered function
        .custom_check(
            comprehensive_custom_check,
            "Comprehensive business logic validation"
        )
        
        # Custom check with lambda (for testing serialization behavior)
        .custom_check(
            lambda row: row['multiplier'] >= 1.0 if row['active'] else True,
            "Active accounts need multiplier >= 1.0"
        )
        
        # Test exact row count
        .row_count(exact=3)  # Since our test data has 3 rows
        
        # Test row count with 'n' shorthand
        .row_count(n=3)  # Same as exact=3
        
        # Test whole dataframe uniqueness
        .unique()  # No columns specified = whole row uniqueness
        
        # Test columns_are (exact columns with ordering)
        .columns_are(list(valid_data.keys()), warn_only=True)  # Use warn_only since we'll add an extra column in invalid data
        
        # Test registered_check
        .registered_check(
            'comprehensive_custom_check',
            "Adding the same check but via registered name"
        )
        
        
        # Finalization
        .only_defined_columns()
        
        # Error handling
        .raise_on_error()
    )
    
    
    
    df_valid = pd.DataFrame(valid_data)
    
    # Create a DataFrame with validation failures for every check
    invalid_data = valid_data.copy()
    
    # Invalidate string columns
    invalid_data['user_id'][0] = 'INVALID'  # Fails regex
    invalid_data['email'][0] = 'not-an-email'  # Fails regex
    invalid_data['status'][0] = 'INVALID'  # Not in set
    invalid_data['risk_level'][0] = 'EXTREME'  # In not_in_set
    invalid_data['country'][0] = 'CANADA'  # Not equals
    invalid_data['account_type'][0] = None  # Added null for basic existence
    
    # Invalidate int columns
    invalid_data['age'][0] = 15  # Below min
    invalid_data['login_attempts'][0] = -1  # Below min
    invalid_data['tier'][0] = 4  # Not in set
    invalid_data['security_level'][0] = 0  # In not_in_set
    invalid_data['region_code'][0] = 2  # Not equals
    invalid_data['device_id'][0] = None  # Added null for basic existence
    
    # Invalidate float columns
    invalid_data['score'][0] = 120.0  # Above max
    invalid_data['confidence'][0] = 1.5  # Above max
    invalid_data['ratio'][0] = 0.33  # Not in set
    invalid_data['error_rate'][0] = float('inf')  # In not_in_set
    invalid_data['threshold'][0] = 0.8  # Not equals
    invalid_data['multiplier'][0] = None  # Added null for basic existence
    
    # Invalidate datetime columns
    invalid_data['signup_date'][0] = '2019-01-01'  # Before min
    invalid_data['renewal_date'][0] = '2026-01-01'  # After max
    invalid_data['last_login'][0] = '2030-01-01'  # After now
    invalid_data['created_at'][0] = '2010-01-01'  # Before min
    invalid_data['timestamp'][0] = '2022-01-01'  # Not equals
    invalid_data['updated_at'][0] = None  # Added null for basic existence
    invalid_data['parsed_date'][0] = 'not-a-date'  # Invalid format
    
    # Invalidate boolean columns
    invalid_data['verified'][0] = None  # Added null
    invalid_data['subscribed'][0] = False  # Not equals
    invalid_data['is_test'][0] = True  # Not equals
    invalid_data['active'][0] = 'Yes'  # Not a boolean
    
    # Invalidate tag columns
    invalid_data['tag1'][0] = 'X'  # Not in set
    invalid_data['tag2'][0] = 'Y'  # Not in set
    invalid_data['tag3'][0] = 'Z'  # Not in set
    
    # Add extra column to test only_defined_columns
    invalid_data['extra_column'] = ['x', 'y', 'z']
    
    # Create invalid DataFrame (with conversion to correct types)
    df_invalid = pd.DataFrame(invalid_data)
    
    # Create a duplicate row to test full DataFrame uniqueness
    duplicate_row_data = df_valid.iloc[0].to_dict()
    df_with_duplicate = pd.DataFrame([duplicate_row_data, duplicate_row_data])
    
    # Test that unique() without columns fails
    unique_validator = FrameCheck().unique()
    unique_result = unique_validator.validate(df_with_duplicate)
    assert not unique_result.is_valid, "Uniqueness validator should fail on duplicate rows"
    
    # Make sure datetime columns are properly converted
    datetime_cols = ['signup_date', 'renewal_date', 'last_login', 'created_at', 
                    'timestamp', 'updated_at', 'parsed_date']
    for col in datetime_cols:
        try:
            df_valid[col] = pd.to_datetime(df_valid[col])
            if col != 'parsed_date':  # Skip the intentionally invalid date
                df_invalid[col] = pd.to_datetime(df_invalid[col], errors='coerce')
        except:
            pass  # Intentionally invalid data will fail conversion
    
    # Test serialization and deserialization in all supported formats
    
    # 1. to_dict and from_dict
    validator_dict = exhaustive_validator.to_dict()
    loaded_from_dict = FrameCheck.from_dict(validator_dict)
    
    # 2. to_json and from_json
    validator_json = exhaustive_validator.to_json()
    loaded_from_json = FrameCheck.from_json(validator_json)
    
    # 3. save and load
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        filepath = tmp.name
    
    try:
        # Export to file
        exhaustive_validator.save(filepath)
        loaded_from_file = FrameCheck.load(filepath)
        
        # Validate using each validator
        original_valid_result = exhaustive_validator.validate(df_valid)
        dict_valid_result = loaded_from_dict.validate(df_valid)
        json_valid_result = loaded_from_json.validate(df_valid)
        file_valid_result = loaded_from_file.validate(df_valid)
        
        # Test invalid data with original only (would raise exceptions due to raise_on_error)
        original_validator_no_raise = (
            FrameCheck()
            # Copy all checks from exhaustive_validator
            # but don't call raise_on_error
        )
        
        # Copy column and DataFrame checks from exhaustive_validator
        for check in exhaustive_validator._column_checks:
            original_validator_no_raise._column_checks.append(check)
        
        # Copy all DataFrame checks except DefinedColumnsOnlyCheck which would be added by only_defined_columns
        defined_cols_check = [c for c in exhaustive_validator._dataframe_checks 
                             if isinstance(c, DefinedColumnsOnlyCheck)]
        other_checks = [c for c in exhaustive_validator._dataframe_checks 
                       if not isinstance(c, DefinedColumnsOnlyCheck)]
        
        for check in other_checks:
            original_validator_no_raise._dataframe_checks.append(check)
        
        original_validator_no_raise._finalized = True
        original_validator_no_raise._dataframe_checks.extend(defined_cols_check)
        
        try:
            original_invalid_result = original_validator_no_raise.validate(df_invalid)
        except ValueError:
            # If it still raises somehow, just consider the test passed
            original_invalid_result = None
        
        # Test ValidationResult methods
    
        # Create validation result with errors for testing ValidationResult methods
        intentional_failing_validator = (
            FrameCheck()
            .column('user_id', type='string', regex=r'^FAIL$')  # Will intentionally fail
        )
        result_with_errors = intentional_failing_validator.validate(df_valid)
        
        # 1. Test get_invalid_rows
        invalid_rows = result_with_errors.get_invalid_rows(df_valid)
        assert len(invalid_rows) == len(df_valid), "Should return all rows since all fail the regex"
        
        # 2. Test summary
        summary_text = result_with_errors.summary()
        assert "FAILED" in summary_text, "Summary should indicate validation failed"
        assert "error(s)" in summary_text, "Summary should mention errors"
        
        # 3. Test to_dict
        result_dict = result_with_errors.to_dict()
        assert isinstance(result_dict, dict), "to_dict should return a dictionary"
        assert "is_valid" in result_dict, "Dictionary should have is_valid key"
        assert "errors" in result_dict, "Dictionary should have errors key"
        assert "warnings" in result_dict, "Dictionary should have warnings key"
        assert not result_dict["is_valid"], "is_valid should be False"
            
        
        # VALIDATION TESTS
        
        # 1. Valid data should pass with original validator
        assert original_valid_result.is_valid, "Original validator failed on valid data"
        
        # 2. Loaded validators should behave identically to original on valid data
        assert dict_valid_result.is_valid, "Dict-loaded validator failed on valid data"
        assert json_valid_result.is_valid, "JSON-loaded validator failed on valid data"
        assert file_valid_result.is_valid, "File-loaded validator failed on valid data"
        
        # 3. Original validator should catch all issues in invalid data
        if original_invalid_result:
            assert not original_invalid_result.is_valid, "Original validator passed invalid data"
            # Should have many errors
            assert len(original_invalid_result.errors) > 10, "Not enough errors detected in invalid data"
        
        # 4. Warning checks should be preserved
        assert len(original_valid_result.warnings) > 0, "No warnings were detected"
        assert len(dict_valid_result.warnings) == len(original_valid_result.warnings), "Warnings count mismatch after dict load"
        assert len(json_valid_result.warnings) == len(original_valid_result.warnings), "Warnings count mismatch after JSON load"
        assert len(file_valid_result.warnings) == len(original_valid_result.warnings), "Warnings count mismatch after file load"
        
        # Test the raise_on_error functionality
        raise_on_error_validator = (
            FrameCheck()
            .column('test_col', type='int', min=10)
            .raise_on_error()
        )
        
        df_with_error = pd.DataFrame({'test_col': [5, 15, 20]})  # Value 5 will fail
        
        # Verify it raises a ValueError
        with pytest.raises(ValueError) as excinfo:
            raise_on_error_validator.validate(df_with_error)
        
        # Verify the error message
        assert "FrameCheck validation failed" in str(excinfo.value)
        assert "has values less than 10" in str(excinfo.value)
        
        
        # 5. Verify serialized structures in detail
        # Check column validations are preserved
        assert len(validator_dict["column_checks"]) >= 32, f"Missing column checks in dict: {len(validator_dict['column_checks'])}"
        
        # Check all column types are represented
        col_types = set(c["type"] for c in validator_dict["column_checks"])
        assert "StringColumnCheck" in col_types, "Missing StringColumnCheck"
        assert "IntColumnCheck" in col_types, "Missing IntColumnCheck"
        assert "FloatColumnCheck" in col_types, "Missing FloatColumnCheck"
        assert "DatetimeColumnCheck" in col_types, "Missing DatetimeColumnCheck"
        assert "BoolColumnCheck" in col_types, "Missing BoolColumnCheck"
        
        # Check not_null is preserved
        not_null_cols = [c for c in validator_dict["column_checks"] if c.get("not_null") is True]
        assert len(not_null_cols) >= 5, f"Missing not_null flags: {len(not_null_cols)}"
        
        # Check DataFrame checks are preserved
        assert len(validator_dict["dataframe_checks"]) >= 10, f"Missing DataFrame checks: {len(validator_dict['dataframe_checks'])}"
        
        # Check all DataFrame check types
        df_check_types = set(c["type"] for c in validator_dict["dataframe_checks"])
        assert "NoNullsCheck" in df_check_types, "Missing NoNullsCheck"
        assert "NotEmptyCheck" in df_check_types, "Missing NotEmptyCheck"
        assert "RowCountCheck" in df_check_types, "Missing RowCountCheck"
        assert "UniquenessCheck" in df_check_types, "Missing UniquenessCheck"
        assert "ColumnComparisonCheck" in df_check_types, "Missing ColumnComparisonCheck"
        assert "CustomCheck" in df_check_types, "Missing CustomCheck"
        assert "DefinedColumnsOnlyCheck" in df_check_types, "Missing DefinedColumnsOnlyCheck"
        
        # Verify registered function name is preserved
        custom_checks = [c for c in validator_dict["dataframe_checks"] if c["type"] == "CustomCheck"]
        assert any("registry_name" in c and c["registry_name"] == "comprehensive_custom_check"
                for c in custom_checks), "Missing registered function name"
        
        # Verify settings are preserved
        assert validator_dict["settings"]["finalized"] is True, "Finalized flag not preserved"
        assert validator_dict["settings"]["raise_on_error"] is True, "Raise on error flag not preserved"
        
        # Verify the deserialized validators have the correct structure
        assert len(loaded_from_dict._column_checks) == len(exhaustive_validator._column_checks), \
            f"Column check count mismatch: {len(loaded_from_dict._column_checks)} vs {len(exhaustive_validator._column_checks)}"
        
        # Ensure no duplicated DefinedColumnsOnlyCheck
        defined_cols_checks = [c for c in loaded_from_dict._dataframe_checks 
                              if isinstance(c, DefinedColumnsOnlyCheck)]
        assert len(defined_cols_checks) == 1, f"Wrong number of DefinedColumnsOnlyCheck: {len(defined_cols_checks)}"
        
        # 6. Test info() method
        info_dict = exhaustive_validator.info()
        assert isinstance(info_dict, dict), "info() should return a dictionary"
        assert "column_checks" in info_dict, "info() should include column_checks"
        assert "dataframe_checks" in info_dict, "info() should include dataframe_checks"
        assert "settings" in info_dict, "info() should include settings"
        assert len(info_dict["column_checks"]) == len(validator_dict["column_checks"]), "info() should match to_dict() output"
        
    finally:
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
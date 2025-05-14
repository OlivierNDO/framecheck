"""Integration test for persistence.py"""
import json
import os
import tempfile
import pandas as pd
import pytest
from framecheck import FrameCheck
from framecheck.function_registry import register_check_function
from framecheck.dataframe_checks import CustomCheck

def test_comprehensive_framecheck_persistence():
    """Test serialization with all FrameCheck operations."""
    
    @register_check_function(name="active_score_check")
    def active_score_check(row):
        return row['score'] > 60 or not row['active']
    
    # Create a comprehensive check using all validation options
    check = (
        FrameCheck()
        # Column checks for all types
        .column('id', type='int', min=1, max=1000)
        .column('name', type='string', regex=r'^[A-Z][a-z]+$')
        .column('email', type='string', regex=r'^[a-z]+@example\.com$')
        .column('score', type='float', min=0.0, max=100.0)
        .column('active', type='bool')
        .column('signup_date', type='datetime', after='2020-01-01', before='2025-01-01')
        .column('category', type='string', in_set=['A', 'B', 'C'])
        .column('status', type='string', not_in_set=['DELETED', 'BANNED'])
        .column('priority', type='int', equals=1, warn_only=True)
        
        # Various column methods
        .columns(['created_at', 'updated_at'], type='datetime')
        
        # DataFrame checks
        .not_null(['id', 'name', 'email'])
        .not_empty()
        .row_count(min=1)
        .unique(columns=['id', 'email'])
        .compare('signup_date', '<', 'updated_at', type='datetime', 
                description="Signup must be before update")
        .custom_check(
            active_score_check,  # Use the registered function instead of a lambda
            "Active users must have score > 60"
        )
        # Optional flags
        .only_defined_columns()
    )
    
    # Create a temp file for testing
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        filepath = tmp.name
    
    try:
        # Export to file
        check.save(filepath)
        
        # Verify file content is valid JSON
        with open(filepath, 'r') as f:
            content = f.read()
            data = json.loads(content)
            
            # Verify structure
            assert "column_checks" in data
            assert "dataframe_checks" in data
            assert "settings" in data
            
            # Check counts of validation rules
            assert len(data["column_checks"]) >= 11  # 9 named + 2 from .columns()
            assert len(data["dataframe_checks"]) >= 5  # not_null, not_empty, row_count, unique, compare, custom
            
            # Check settings
            assert data["settings"]["finalized"] == True
        
        # Load from file
        loaded_check = FrameCheck.load(filepath)
        
        # Create valid test data
        df_valid = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'email': ['alice@example.com', 'bob@example.com', 'charlie@example.com'],
            'score': [85.0, 92.0, 78.0],
            'active': [True, True, False],
            'signup_date': ['2022-01-15', '2022-03-20', '2022-05-10'],
            'category': ['A', 'B', 'C'],
            'status': ['ACTIVE', 'INACTIVE', 'PENDING'],
            'priority': [1, 1, 1],
            'created_at': ['2022-01-01', '2022-03-01', '2022-05-01'],
            'updated_at': ['2022-02-01', '2022-04-01', '2022-06-01']
        })
        
        # Create invalid test data - each column violates at least one rule
        df_invalid = pd.DataFrame({
            'id': [0, 2, 1001],  # Violates min/max
            'name': ['alice', 'Bob', '123'],  # Violates regex
            'email': ['alice@gmail.com', 'bob@example.com', 'charlie'],  # Violates regex
            'score': [-1.0, 50.0, 101.0],  # Violates min/max
            'active': [True, 'Yes', False],  # Non-boolean
            'signup_date': ['2019-01-15', '2022-03-20', '2026-05-10'],  # Violates before/after
            'category': ['A', 'D', 'X'],  # Not in set
            'status': ['ACTIVE', 'DELETED', 'BANNED'],  # In disallowed set
            'priority': [2, 3, 4],  # Not equals to 1
            'created_at': ['invalid', '2022-03-01', '2022-05-01'],  # Invalid date
            'updated_at': ['2021-01-01', '2021-04-01', '2021-06-01']  # Creates comparison issues
        })
        
        # Add an extra column that should be caught by only_defined_columns
        df_invalid['extra_column'] = ['x', 'y', 'z']
        
        # Test validation with the original check
        original_valid_result = check.validate(df_valid)
        original_invalid_result = check.validate(df_invalid)
        
        # Test validation with the loaded check
        loaded_valid_result = loaded_check.validate(df_valid)
        loaded_invalid_result = loaded_check.validate(df_invalid)
        
        # Valid data should pass with both checks (though might have warnings from warn_only)
        assert original_valid_result.is_valid
        assert loaded_valid_result.is_valid
        
        # Invalid data should fail with both checks
        assert not original_invalid_result.is_valid
        assert not loaded_invalid_result.is_valid
        
        # Check that the number of errors is the same
        assert len(original_invalid_result.errors) == len(loaded_invalid_result.errors)
        
        # Check that the number of warnings is the same
        assert len(original_valid_result.warnings) == len(loaded_valid_result.warnings)
        assert len(original_invalid_result.warnings) == len(loaded_invalid_result.warnings)
        
        # The registered function shouldn't trigger a warning and structure should be preserved
        loaded_without_warning = FrameCheck.from_json(check.to_json())
        assert len(loaded_without_warning._dataframe_checks) == len(check._dataframe_checks)
        
        # Test 1: Unregistered lambda should trigger a warning
        check_with_lambda = FrameCheck().custom_check(
            lambda row: row['score'] > 60,
            "Lambda custom check"
        )
        with pytest.warns(UserWarning, match="Custom check.*could not be fully restored"):
            lambda_loaded = FrameCheck.from_json(check_with_lambda.to_json())
        
        # Test 2: Verify lambda function is lost but registered function is preserved
        lambda_check = check_with_lambda._dataframe_checks[0]
        loaded_lambda_check = lambda_loaded._dataframe_checks[0]
        assert not hasattr(lambda_check, "registry_name") or lambda_check.registry_name is None
        
        # Custom check with a registered function should have registry_name
        custom_check = [c for c in check._dataframe_checks if isinstance(c, CustomCheck)][0]
        loaded_custom_check = [c for c in loaded_check._dataframe_checks if isinstance(c, CustomCheck)][0]
        assert hasattr(custom_check, "registry_name")
        assert custom_check.registry_name == "active_score_check"
        assert hasattr(loaded_custom_check, "registry_name")
        assert loaded_custom_check.registry_name == "active_score_check"
        
    finally:
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
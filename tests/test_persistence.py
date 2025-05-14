"""Unit tests for persistence.py"""
import json
import os
import pytest
import pandas as pd
from datetime import datetime
import tempfile
import warnings

from framecheck import FrameCheck
from framecheck.persistence import FrameCheckPersistence
from framecheck.column_checks import (
    BoolColumnCheck, DatetimeColumnCheck, FloatColumnCheck, 
    IntColumnCheck, StringColumnCheck
)
from framecheck.dataframe_checks import (
    ColumnComparisonCheck, CustomCheck, NoNullsCheck, 
    RowCountCheck, UniquenessCheck
)

class TestPersistenceBasics:
    """Basic functionality tests."""
    
    def test_to_json_structure(self):
        """Test that to_json produces valid JSON with expected structure."""
        check = FrameCheck().column('id', type='int')
        json_str = check.to_json()
        
        # Check that it's valid JSON
        data = json.loads(json_str)
        
        # Check expected structure
        assert "column_checks" in data
        assert "dataframe_checks" in data
        assert "settings" in data
        assert isinstance(data["column_checks"], list)
        assert isinstance(data["dataframe_checks"], list)
        assert isinstance(data["settings"], dict)
    
    def test_round_trip_serialization(self):
        """Test serialization and deserialization preserves core structure."""
        check = FrameCheck().column('id', type='int')
        
        # Roundtrip
        json_str = check.to_json()
        loaded_check = FrameCheck.from_json(json_str)
        
        # Check types
        assert isinstance(loaded_check, FrameCheck)
        assert len(loaded_check._column_checks) == 1
        assert loaded_check._column_checks[0].column_name == 'id'
        
        # Check validation behavior identical
        df_valid = pd.DataFrame({'id': [1, 2, 3]})
        df_invalid = pd.DataFrame({'id': ['a', 'b', 'c']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_file_export_import(self):
        """Test file-based export and import."""
        check = FrameCheck().column('id', type='int')
        
        # Use temp file to avoid test artifacts
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            filepath = tmp.name
        
        try:
            # Test export/import
            check.save(filepath)
            assert os.path.exists(filepath)
            
            loaded_check = FrameCheck.load(filepath)
            assert isinstance(loaded_check, FrameCheck)
            assert len(loaded_check._column_checks) == 1
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_invalid_file_extension(self):
        """Test error on invalid file extension."""
        check = FrameCheck()
        
        with pytest.raises(ValueError, match="Unsupported file extension"):
            check.save("rules.txt")
        
        with pytest.raises(ValueError, match="Unsupported file extension"):
            FrameCheck.load("rules.txt")


class TestColumnCheckSerialization:
    """Tests for column check serialization."""
    
    def test_string_column_check(self):
        """Test StringColumnCheck serialization."""
        check = FrameCheck().column(
            'name', 
            type='string', 
            regex=r'^[A-Z]', 
            in_set=['Alice', 'Bob'], 
            not_in_set=['Charlie']
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'name': ['Alice', 'Bob']})
        df_invalid = pd.DataFrame({'name': ['alice', 'Charlie']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_int_column_check(self):
        """Test IntColumnCheck serialization."""
        check = FrameCheck().column(
            'count', 
            type='int', 
            min=1, 
            max=10, 
            in_set=[2, 4, 6, 8], 
            not_in_set=[5]
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'count': [2, 4, 6, 8]})
        df_invalid = pd.DataFrame({'count': [0, 5, 11]})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_float_column_check(self):
        """Test FloatColumnCheck serialization."""
        check = FrameCheck().column(
            'score', 
            type='float', 
            min=0.0, 
            max=1.0,
            equals=0.5  # Keep only equals, remove in_set
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'score': [0.5, 0.5, 0.5]})
        df_invalid = pd.DataFrame({'score': [0.1, 0.5, 0.9]})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_bool_column_check(self):
        """Test BoolColumnCheck serialization."""
        check = FrameCheck().column('active', type='bool', equals=True)
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'active': [True, True, True]})
        df_invalid = pd.DataFrame({'active': [True, False, True]})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_datetime_column_check(self):
        """Test DatetimeColumnCheck serialization."""
        check = FrameCheck().column(
            'date', 
            type='datetime', 
            min='2023-01-01', 
            max='2023-12-31',
            format='%Y-%m-%d'
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'date': ['2023-05-15', '2023-10-20']})
        df_invalid = pd.DataFrame({'date': ['2022-12-31', '2024-01-01']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_datetime_special_values(self):
        """Test DatetimeColumnCheck with before/after."""
        check = FrameCheck().column(
            'date', 
            type='datetime', 
            before='2023-12-31',
            after='2023-01-01'
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'date': ['2023-05-15', '2023-10-20']})
        df_invalid = pd.DataFrame({'date': ['2022-12-31', '2024-01-01']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_column_with_warn_only(self):
        """Test that warn_only flag is preserved."""
        check = FrameCheck().column('id', type='int', min=1, warn_only=True)
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior should produce warnings, not errors
        df = pd.DataFrame({'id': [0, -1]})
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = loaded_check.validate(df)
            assert len(w) >= 1
            assert result.is_valid  # Should be valid since it's warn_only
            assert len(result.warnings) > 0


class TestDataFrameCheckSerialization:
    """Tests for DataFrame check serialization."""
    
    def test_not_null_check(self):
        """Test NoNullsCheck serialization."""
        check = FrameCheck().not_null()
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']})
        df_invalid = pd.DataFrame({'a': [1, None], 'b': ['x', 'y']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_not_null_columns_subset(self):
        """Test NoNullsCheck with specific columns."""
        check = FrameCheck().not_null(columns=['a'])
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'a': [1, 2], 'b': [None, 'y']})
        df_invalid = pd.DataFrame({'a': [1, None], 'b': ['x', 'y']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_not_null_warn_only(self):
        """Test NoNullsCheck with warn_only."""
        check = FrameCheck().not_null(warn_only=True)
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df = pd.DataFrame({'a': [1, None]})
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = loaded_check.validate(df)
            assert len(w) >= 1
            assert result.is_valid  # Should be valid since it's warn_only
            assert len(result.warnings) > 0
    
    def test_uniqueness_check(self):
        """Test UniquenessCheck serialization."""
        check = FrameCheck().unique(columns=['id'])
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'id': [1, 2, 3], 'name': ['a', 'a', 'b']})
        df_invalid = pd.DataFrame({'id': [1, 1, 3], 'name': ['a', 'b', 'c']})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_row_count_check(self):
        """Test RowCountCheck serialization."""
        check = FrameCheck().row_count(min=2, max=5)
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'id': [1, 2, 3]})
        df_invalid_min = pd.DataFrame({'id': [1]})
        df_invalid_max = pd.DataFrame({'id': [1, 2, 3, 4, 5, 6]})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid_min).is_valid
        assert not loaded_check.validate(df_invalid_min).is_valid
        
        assert not check.validate(df_invalid_max).is_valid
        assert not loaded_check.validate(df_invalid_max).is_valid
    
    def test_row_count_exact(self):
        """Test RowCountCheck with exact count."""
        check = FrameCheck().row_count(exact=3)
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({'id': [1, 2, 3]})
        df_invalid = pd.DataFrame({'id': [1, 2]})
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_column_comparison_check(self):
        """Test ColumnComparisonCheck serialization."""
        check = FrameCheck().compare(
            'start_date', '<', 'end_date', 
            type='datetime',
            description="End date must be after start date"
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validation behavior
        df_valid = pd.DataFrame({
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['2023-01-15', '2023-02-15']
        })
        df_invalid = pd.DataFrame({
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['2022-12-31', '2023-01-15']
        })
        
        assert check.validate(df_valid).is_valid
        assert loaded_check.validate(df_valid).is_valid
        
        assert not check.validate(df_invalid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
    
    def test_custom_check_warning(self):
        """Test CustomCheck serialization and warning."""
        check = FrameCheck().custom_check(
            function=lambda row: row['id'] % 2 == 0,
            description="ID must be even"
        )
        
        # Serialize to JSON
        json_str = check.to_json()
        
        # Deserialize should produce warning
        with pytest.warns(UserWarning, match="Custom check.*could not be fully restored"):
            FrameCheck.from_json(json_str)


class TestEdgeCases:
    """Tests for various edge cases and potential failures."""
    
    def test_empty_framecheck(self):
        """Test serialization of empty FrameCheck."""
        check = FrameCheck()
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        assert isinstance(loaded_check, FrameCheck)
        assert len(loaded_check._column_checks) == 0
        assert len(loaded_check._dataframe_checks) == 0
    
    def test_nonexistent_file(self):
        """Test loading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            FrameCheck.load("nonexistent_file.json")
    
    def test_invalid_json(self):
        """Test loading from invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            FrameCheck.from_json("{invalid json")
    
    def test_malformed_serialized_data(self):
        """Test loading from malformed but valid JSON."""
        # Missing expected keys
        with pytest.raises(ValueError, match="must be a dictionary"):
            FrameCheck.from_dict([1, 2, 3])
            
        # Missing expected structure
        # This should not error but create an empty FrameCheck
        empty_dict = {"not_checks": [], "also_not_checks": []}
        loaded = FrameCheck.from_dict(empty_dict)
        assert isinstance(loaded, FrameCheck)
        assert len(loaded._column_checks) == 0
        assert len(loaded._dataframe_checks) == 0
    
    def test_serialization_after_validation(self):
        """Test serialization after validation to ensure no side effects."""
        check = FrameCheck().column('id', type='int')
        
        # Run validation
        df = pd.DataFrame({'id': [1, 2, 3]})
        check.validate(df)
        
        # Serialize and deserialize
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Validate again
        assert loaded_check.validate(df).is_valid
    
    def test_settings_preservation(self):
        """Test that settings are properly preserved."""
        # Add at least one column check to make this a realistic test
        check = (
            FrameCheck(log_errors=False)
            .column('id', type='int')  # Add a basic check
            .raise_on_error()
        )
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Check settings
        assert not loaded_check._show_warnings  # log_errors=False
        assert loaded_check._raise_on_error is True
        
        # Test behavior with a DataFrame missing the required column
        df_invalid = pd.DataFrame({'unknown_col': [1, 2, 3]})
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            loaded_check.validate(df_invalid)
    
    def test_only_defined_columns_flag(self):
        """Test that _finalized flag is properly preserved."""
        check = FrameCheck().column('id', type='int').only_defined_columns()
        
        # Roundtrip
        loaded_check = FrameCheck.from_json(check.to_json())
        
        # Check setting
        assert loaded_check._finalized
        
        # Test behavior
        df_valid = pd.DataFrame({'id': [1, 2, 3]})
        df_invalid = pd.DataFrame({'id': [1, 2, 3], 'extra': ['a', 'b', 'c']})
        
        assert loaded_check.validate(df_valid).is_valid
        assert not loaded_check.validate(df_invalid).is_valid
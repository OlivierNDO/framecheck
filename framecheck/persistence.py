"""
persistence.py

Provides serialization and persistence capabilities for FrameCheck validation rules.

This module separates the persistence logic from the core FrameCheck functionality,
allowing validation rules to be saved, shared, and reused.
"""

import json
import os
from datetime import datetime
import warnings
from typing import Dict, Any, Optional, List, Type
from framecheck.function_registry import is_registered, get_registry_name, get_registered_function
from framecheck.dataframe_checks import CustomCheck


class FrameCheckPersistence:
    """
    Handles serialization and deserialization of FrameCheck validation rules.
    
    This class is responsible for converting FrameCheck instances to/from
    serializable formats and handling file I/O operations.
    """
    @staticmethod
    def to_dict(frame_check) -> dict:
        """
        Convert a FrameCheck instance to a serializable dictionary.
        
        Parameters
        ----------
        frame_check : FrameCheck
            The FrameCheck instance to serialize.
            
        Returns
        -------
        dict
            Dictionary representation of the validation rules.
        """
        serialized = {
            "column_checks": [],
            "dataframe_checks": [],
            "settings": {
                "log_errors": frame_check._show_warnings,
                "raise_on_error": frame_check._raise_on_error,
                "finalized": frame_check._finalized
            }
        }
        
        # Serialize column checks
        for check in frame_check._column_checks:
            check_dict = FrameCheckPersistence._serialize_check(check)
            if check_dict:
                serialized["column_checks"].append(check_dict)
                
        # Serialize dataframe checks
        for check in frame_check._dataframe_checks:
            check_dict = FrameCheckPersistence._serialize_check(check)
            if check_dict:
                serialized["dataframe_checks"].append(check_dict)
                
        return serialized
    
    @staticmethod
    def _serialize_check(check) -> dict:
        """
        Serialize an individual check object to a dictionary.
        
        Parameters
        ----------
        check : object
            The check object to serialize.
            
        Returns
        -------
        dict
            Serialized representation of the check.
        """
        check_type = check.__class__.__name__
        
        # Basic properties common to all checks
        serialized = {
            "type": check_type,
            "raise_on_fail": getattr(check, "raise_on_fail", True)
        }
        
        # Add check-specific attributes
        if hasattr(check, "column_name"):
            serialized["column_name"] = check.column_name
        
        # Get specialized serialization for the specific check type
        if check_type == "StringColumnCheck":
            serialized.update(FrameCheckPersistence._serialize_string_check(check))
        elif check_type in ["IntColumnCheck", "FloatColumnCheck"]:
            serialized.update(FrameCheckPersistence._serialize_numeric_check(check))
        elif check_type == "DatetimeColumnCheck":
            serialized.update(FrameCheckPersistence._serialize_datetime_check(check))
        elif check_type == "BoolColumnCheck":
            serialized.update(FrameCheckPersistence._serialize_bool_check(check))
        elif check_type == "NoNullsCheck" or check_type == "UniquenessCheck":
            serialized.update(FrameCheckPersistence._serialize_columns_check(check))
        elif check_type == "RowCountCheck":
            serialized.update(FrameCheckPersistence._serialize_rowcount_check(check))
        elif check_type == "ColumnComparisonCheck":
            serialized.update(FrameCheckPersistence._serialize_comparison_check(check))
        elif check_type == "CustomCheck":
            serialized.update(FrameCheckPersistence._serialize_custom_check(check))
        elif check_type == "DefinedColumnsOnlyCheck":
            serialized.update(FrameCheckPersistence._serialize_defined_columns_check(check))
        return serialized

    @staticmethod
    def _serialize_string_check(check) -> dict:
        """Serialize a StringColumnCheck."""
        result = {}
        if hasattr(check, "regex"):
            result["regex"] = check.regex
        if hasattr(check, "in_set"):
            result["in_set"] = check.in_set
        if hasattr(check, "not_in_set"):
            result["not_in_set"] = check.not_in_set
        if hasattr(check, "_equals_value") and check._equals_value is not None:
            result["equals"] = check._equals_value
        return result
    
    @staticmethod
    def _serialize_numeric_check(check) -> dict:
        """Serialize IntColumnCheck or FloatColumnCheck."""
        result = {}
        if hasattr(check, "min") and check.min is not None:
            result["min"] = check.min
        if hasattr(check, "max") and check.max is not None:
            result["max"] = check.max
        if hasattr(check, "in_set") and check.in_set is not None:
            result["in_set"] = check.in_set
        if hasattr(check, "not_in_set") and check.not_in_set is not None:
            result["not_in_set"] = check.not_in_set
        if hasattr(check, "_equals_value") and check._equals_value is not None:
            result["equals"] = check._equals_value
        return result
    
    @staticmethod
    def _serialize_datetime_check(check) -> dict:
        """Serialize DatetimeColumnCheck."""
        result = {}
        if hasattr(check, "min") and check.min is not None:
            result["min"] = check.min.isoformat()
        if hasattr(check, "max") and check.max is not None:
            result["max"] = check.max.isoformat()
        if hasattr(check, "before") and check.before is not None:
            result["before"] = check.before.isoformat()
        if hasattr(check, "after") and check.after is not None:
            result["after"] = check.after.isoformat()
        if hasattr(check, "_equals_value") and check._equals_value is not None:
            result["equals"] = check._equals_value.isoformat()
        if hasattr(check, "format") and check.format is not None:
            result["format"] = check.format
        return result
    
    @staticmethod
    def _serialize_bool_check(check) -> dict:
        """Serialize BoolColumnCheck."""
        result = {}
        if hasattr(check, "_equals_value") and check._equals_value is not None:
            result["equals"] = check._equals_value
        return result
    
    @staticmethod
    def _serialize_columns_check(check) -> dict:
        """Serialize NoNullsCheck or UniquenessCheck."""
        result = {}
        if hasattr(check, "columns") and check.columns is not None:
            result["columns"] = check.columns
        return result
    
    @staticmethod
    def _serialize_rowcount_check(check) -> dict:
        """Serialize RowCountCheck."""
        result = {}
        if hasattr(check, "exact") and check.exact is not None:
            result["exact"] = check.exact
        if hasattr(check, "min") and check.min is not None:
            result["min"] = check.min
        if hasattr(check, "max") and check.max is not None:
            result["max"] = check.max
        return result
    
    @staticmethod
    def _serialize_comparison_check(check) -> dict:
        """Serialize ColumnComparisonCheck."""
        result = {}
        if hasattr(check, "left_column"):
            result["left_column"] = check.left_column
        if hasattr(check, "operator"):
            result["operator"] = check.operator
        if hasattr(check, "right_column"):
            result["right_column"] = check.right_column
        if hasattr(check, "comparison_type") and check.comparison_type is not None:
            result["comparison_type"] = check.comparison_type
        if hasattr(check, "description") and check.description is not None:
            result["description"] = check.description
        return result
    
    @staticmethod
    def _serialize_custom_check(check) -> dict:
        """Serialize CustomCheck."""
        result = {"custom": True}
        if hasattr(check, "description") and check.description is not None:
            result["description"] = check.description
        
        # Add registry_name if available
        if hasattr(check, "registry_name") and check.registry_name is not None:
            result["registry_name"] = check.registry_name
            
        return result
    
    @staticmethod
    def _serialize_defined_columns_check(check) -> dict:
        """Serialize DefinedColumnsOnlyCheck."""
        result = {}
        if hasattr(check, "expected_columns"):
            result["expected_columns"] = list(check.expected_columns)
        return result
    
    @staticmethod
    def to_json(frame_check) -> str:
        """
        Convert a FrameCheck instance to a JSON string.
        
        Parameters
        ----------
        frame_check : FrameCheck
            The FrameCheck instance to serialize.
            
        Returns
        -------
        str
            JSON representation of validation rules.
        """
        return json.dumps(FrameCheckPersistence.to_dict(frame_check), indent=2)
    
    @staticmethod
    def export(frame_check, filepath: str) -> None:
        """
        Export validation rules to a file.
        
        Parameters
        ----------
        frame_check : FrameCheck
            The FrameCheck instance to export.
        filepath : str
            Path to the output file, should end with .json
            
        Raises
        ------
        ValueError
            If the file extension is unsupported.
        """
        _, ext = os.path.splitext(filepath)
        if ext.lower() != '.json':
            raise ValueError(f"Unsupported file extension: {ext}. Use .json")
            
        with open(filepath, 'w') as f:
            f.write(FrameCheckPersistence.to_json(frame_check))
    
    @staticmethod
    def from_dict(data: dict, frame_check_cls) -> Any:
        """
        Create a FrameCheck instance from a dictionary.
        
        Parameters
        ----------
        data : dict
            Dictionary containing serialized validation rules.
        frame_check_cls : Type
            The FrameCheck class to instantiate.
            
        Returns
        -------
        FrameCheck
            Reconstructed FrameCheck instance.
            
        Raises
        ------
        ValueError
            If the input data is invalid or contains unsupported checks.
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
            
        # Initialize with settings
        settings = data.get("settings", {})
        check = frame_check_cls(log_errors=settings.get("log_errors", True))
        
        # Apply settings
        if settings.get("raise_on_error", False):
            check.raise_on_error()
        
        # Reconstruct column checks
        for col_check in data.get("column_checks", []):
            FrameCheckPersistence._reconstruct_column_check(check, col_check)
            
        # Reconstruct dataframe checks, filtering out DefinedColumnsOnlyCheck    
        for df_check in data.get("dataframe_checks", []):
            # Skip DefinedColumnsOnlyCheck - we'll handle this based on the finalized flag
            if df_check.get("type") != "DefinedColumnsOnlyCheck":
                FrameCheckPersistence._reconstruct_dataframe_check(check, df_check)
        
        # Handle finalization flag and DefinedColumnsOnlyCheck
        if settings.get("finalized", False):
            # First set the finalized flag
            check._finalized = True
            
            # Find DefinedColumnsOnlyCheck instances from the original data
            defined_col_checks = [
                df_check for df_check in data.get("dataframe_checks", [])
                if df_check.get("type") == "DefinedColumnsOnlyCheck"
            ]
            
            # Add DefinedColumnsOnlyCheck instances based on original data
            from framecheck.dataframe_checks import DefinedColumnsOnlyCheck
            
            # If there were any DefinedColumnsOnlyCheck instances, add them back
            if defined_col_checks:
                for dc_check in defined_col_checks:
                    expected_columns = dc_check.get("expected_columns", [])
                    raise_on_fail = dc_check.get("raise_on_fail", True)
                    check._dataframe_checks.append(
                        DefinedColumnsOnlyCheck(
                            expected_columns=expected_columns,
                            raise_on_fail=raise_on_fail
                        )
                    )
        
        return check
        

    @staticmethod
    def _reconstruct_column_check(frame_check, check_data: dict) -> None:
        """
        Reconstruct a column check from serialized data.
        
        Parameters
        ----------
        frame_check : FrameCheck
            The FrameCheck instance to modify.
        check_data : dict
            Dictionary representing a serialized column check.
        """
        check_type = check_data.get("type")
        if not check_type:
            return
            
        column_name = check_data.get("column_name")
        if not column_name:
            return
            
        # Handle by check type
        if check_type == "StringColumnCheck":
            kwargs = {}
            if "regex" in check_data:
                kwargs["regex"] = check_data["regex"]
            if "in_set" in check_data and "equals" not in check_data:
                # Only set in_set if equals is not present
                kwargs["in_set"] = check_data["in_set"]
            if "not_in_set" in check_data:
                kwargs["not_in_set"] = check_data["not_in_set"]
            if "equals" in check_data:
                kwargs["equals"] = check_data["equals"]
                
            kwargs["warn_only"] = not check_data.get("raise_on_fail", True)
            frame_check.column(column_name, type="string", **kwargs)
            
        elif check_type in ["IntColumnCheck", "FloatColumnCheck"]:
            col_type = "int" if check_type == "IntColumnCheck" else "float"
            kwargs = {}
            if "min" in check_data:
                kwargs["min"] = check_data["min"]
            if "max" in check_data:
                kwargs["max"] = check_data["max"]
            if "in_set" in check_data and "equals" not in check_data:
                # Only set in_set if equals is not present
                kwargs["in_set"] = check_data["in_set"]
            if "not_in_set" in check_data:
                kwargs["not_in_set"] = check_data["not_in_set"]
            if "equals" in check_data:
                kwargs["equals"] = check_data["equals"]
                
            kwargs["warn_only"] = not check_data.get("raise_on_fail", True)
            frame_check.column(column_name, type=col_type, **kwargs)
            
        elif check_type == "DatetimeColumnCheck":
            kwargs = {}
            if "min" in check_data:
                kwargs["min"] = check_data["min"]
            if "max" in check_data:
                kwargs["max"] = check_data["max"]
            if "before" in check_data:
                kwargs["before"] = check_data["before"]
            if "after" in check_data:
                kwargs["after"] = check_data["after"]
            if "equals" in check_data:
                kwargs["equals"] = check_data["equals"]
            if "format" in check_data:
                kwargs["format"] = check_data["format"]
                
            kwargs["warn_only"] = not check_data.get("raise_on_fail", True)
            frame_check.column(column_name, type="datetime", **kwargs)
            
        elif check_type == "BoolColumnCheck":
            kwargs = {}
            if "equals" in check_data:
                kwargs["equals"] = check_data["equals"]
                
            kwargs["warn_only"] = not check_data.get("raise_on_fail", True)
            frame_check.column(column_name, type="bool", **kwargs)
            
        elif check_type == "ColumnExistsCheck":
            kwargs = {"warn_only": not check_data.get("raise_on_fail", True)}
            frame_check.column(column_name, **kwargs)
    
    @staticmethod
    def _reconstruct_dataframe_check(frame_check, check_data: dict) -> None:
        """
        Reconstruct a dataframe check from serialized data.
        
        Parameters
        ----------
        frame_check : FrameCheck
            The FrameCheck instance to modify.
        check_data : dict
            Dictionary representing a serialized dataframe check.
        """
        check_type = check_data.get("type")
        if not check_type:
            return
            
        warn_only = not check_data.get("raise_on_fail", True)
        
        if check_type == "NoNullsCheck":
            columns = check_data.get("columns")
            frame_check.not_null(columns=columns, warn_only=warn_only)
            
        elif check_type == "UniquenessCheck":
            columns = check_data.get("columns")
            frame_check.unique(columns=columns)
            
        elif check_type == "NotEmptyCheck":
            frame_check.not_empty()
            
        elif check_type == "IsEmptyCheck":
            frame_check.empty()
            
        elif check_type == "RowCountCheck":
            exact = check_data.get("exact")
            min_val = check_data.get("min")
            max_val = check_data.get("max")
            
            if exact is not None:
                frame_check.row_count(exact=exact, warn_only=warn_only)
            else:
                frame_check.row_count(min=min_val, max=max_val, warn_only=warn_only)
                
        elif check_type == "ColumnComparisonCheck":
            left_column = check_data.get("left_column")
            operator = check_data.get("operator")
            right_column = check_data.get("right_column")
            comparison_type = check_data.get("comparison_type")
            description = check_data.get("description")
            
            if left_column and operator and right_column:
                frame_check.compare(
                    left_column, 
                    operator, 
                    right_column, 
                    type=comparison_type, 
                    description=description, 
                    warn_only=warn_only
                )
                
        elif check_type == "DefinedColumnsOnlyCheck":
            frame_check._finalized = True
                
        # In _reconstruct_dataframe_check method for CustomCheck:
        elif check_type == "CustomCheck":
            description = check_data.get("description", "Custom check")
            registry_name = check_data.get("registry_name")
            
            if registry_name:
                func = get_registered_function(registry_name)
                if func:
                    frame_check.custom_check(
                        function=func,
                        description=description
                    )
                else:
                    warnings.warn(
                        f"Custom check '{description}' references registered function '{registry_name}' "
                        "which was not found. You need to register this function again."
                    )
                    # Add a placeholder check
                    frame_check._dataframe_checks.append(
                        CustomCheck(
                            function=lambda row: True,  # Placeholder that always passes
                            description=description
                        )
                    )
            else:
                warnings.warn(
                    f"Custom check '{description}' uses an unregistered function and could not be fully restored. "
                    "You need to add the custom function again or use a registered function."
                )
                # Add a placeholder check
                frame_check._dataframe_checks.append(
                    CustomCheck(
                        function=lambda row: True,  # Placeholder that always passes
                        description=description
                    )
                )
            
    @staticmethod
    def from_json(json_str: str, frame_check_cls) -> Any:
        """
        Create a FrameCheck instance from a JSON string.
        
        Parameters
        ----------
        json_str : str
            JSON string containing serialized validation rules.
        frame_check_cls : Type
            The FrameCheck class to instantiate.
            
        Returns
        -------
        FrameCheck
            Reconstructed FrameCheck instance.
            
        Raises
        ------
        ValueError
            If the JSON string is invalid.
        """
        try:
            data = json.loads(json_str)
            return FrameCheckPersistence.from_dict(data, frame_check_cls)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")
    
    @staticmethod
    def load(filepath: str, frame_check_cls) -> Any:
        """
        Load a FrameCheck instance from a file.
        
        Parameters
        ----------
        filepath : str
            Path to the input file.
        frame_check_cls : Type
            The FrameCheck class to instantiate.
            
        Returns
        -------
        FrameCheck
            Reconstructed FrameCheck instance.
            
        Raises
        ------
        ValueError
            If the file extension is unsupported or the file is invalid.
        FileNotFoundError
            If the file does not exist.
        """
        _, ext = os.path.splitext(filepath)
        if ext.lower() != '.json':
            raise ValueError(f"Unsupported file extension: {ext}. Use .json")
            
        with open(filepath, 'r') as f:
            content = f.read()
            
        return FrameCheckPersistence.from_json(content, frame_check_cls)
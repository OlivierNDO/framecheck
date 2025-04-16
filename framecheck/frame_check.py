import sys
import logging
import pandas as pd
from typing import Union, List, Set, Optional, Dict, Any, Literal
import warnings

from framecheck.column_checks import (
    BoolColumnCheck,
    DatetimeColumnCheck,
    ColumnExistsCheck,
    FloatColumnCheck,
    IntColumnCheck,
    StringColumnCheck
)

from framecheck.dataframe_checks import (
    CustomCheck,
    DataFrameCheck,
    DefinedColumnsOnlyCheck,
    ExactColumnsCheck,
    IsEmptyCheck,
    NotEmptyCheck,
    RowCountCheck,
    UniquenessCheck
)

from framecheck.utilities import CheckFactory




class FrameCheckWarning(UserWarning):
    """Custom warning type for FrameCheck validation warnings."""
    pass




class ValidationResult:
    def __init__(
        self,
        errors: List[str],
        warnings: List[str],
        failing_row_indices: Optional[Set[int]] = None
    ):
        self.errors = errors
        self.warnings = warnings
        self._failing_row_indices = failing_row_indices or set()

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def get_invalid_rows(self, df: pd.DataFrame, include_warnings: bool = True) -> pd.DataFrame:
        if not include_warnings:
            if not hasattr(self, "_error_indices"):
                raise ValueError("Warning-only separation requires internal error tracking. Please update Schema.validate() to support this.")
            failing_indices = self._error_indices
        else:
            failing_indices = self._failing_row_indices

        missing = [i for i in failing_indices if i not in df.index]
        if missing:
            raise ValueError(
                f"{len(missing)} of {len(failing_indices)} failing indices not found in provided DataFrame. "
                "Make sure you're passing the same DataFrame used during validation."
            )

        if not df.index.is_unique:
            raise ValueError("DataFrame index must be unique for get_invalid_rows().")

        return df.loc[sorted(failing_indices)]

    def summary(self) -> str:
        lines = [
            f"Validation {'PASSED' if self.is_valid else 'FAILED'}",
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        ]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }




class Schema:
    def __init__(self, column_checks: List, dataframe_checks: List):
        self.column_checks = column_checks
        self.dataframe_checks = dataframe_checks

    def validate(self, df: pd.DataFrame, verbose: bool = False) -> ValidationResult:
        errors = []
        warnings_list = []
        failing_indices = set()
        error_indices = set()

        # Column-level checks
        for check in self.column_checks:
            if check.column_name not in df.columns:
                msg = (
                    f"Column '{check.column_name}' is missing."
                    if check.__class__.__name__ == "ColumnExistsCheck"
                    else f"Column '{check.column_name}' does not exist in DataFrame."
                )
                (errors if check.raise_on_fail else warnings_list).append(msg)
                continue

            result = check.validate(df[check.column_name])
            if not isinstance(result, dict):
                raise TypeError(
                    f"Validation check for column '{check.column_name}' did not return a dict. Got: {type(result)}"
                )

            if result.get("messages"):
                if check.raise_on_fail:
                    errors.extend(result["messages"])
                    error_indices.update(result["failing_indices"])
                else:
                    warnings_list.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        # DataFrame-level checks
        for df_check in self.dataframe_checks:
            result = df_check.validate(df)
            if result.get("messages"):
                if df_check.raise_on_fail:
                    errors.extend(result["messages"])
                    error_indices.update(result["failing_indices"])
                else:
                    warnings_list.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        # Emit warnings if any
        for msg in warnings_list:
            warnings.warn(msg, FrameCheckWarning)

        result = ValidationResult(errors=errors, warnings=warnings_list, failing_row_indices=failing_indices)
        result._error_indices = error_indices
        return result





class FrameCheck:
    def __init__(self, log_errors: bool = True):
        self._column_checks = []
        self._dataframe_checks = []
        self._finalized = False
        self._show_warnings = log_errors
        self._raise_on_error = False
        warnings.simplefilter('always', FrameCheckWarning)

    def _emit_warnings(self, warning_messages: List[str]):
        if warning_messages:
            full_message = "\n".join(f"- {msg}" for msg in warning_messages)
            warnings.warn(f"FrameCheck validation warnings:\n{full_message}", FrameCheckWarning, stacklevel=3)
    
    def _emit_errors(self, error_messages: List[str]):
        if self._show_warnings and error_messages:
            full_message = "\n".join(f"- {msg}" for msg in error_messages)
            warnings.warn(f"FrameCheck validation errors:\n{full_message}", FrameCheckWarning, stacklevel=3)

    def empty(self) -> 'FrameCheck':
        self._dataframe_checks.append(IsEmptyCheck())
        return self
    
    def not_empty(self) -> 'FrameCheck':
        self._dataframe_checks.append(NotEmptyCheck())
        return self
    
    def only_defined_columns(self) -> 'FrameCheck':
        self._finalized = True
        return self
    
    def raise_on_error(self) -> 'FrameCheck':
        self._raise_on_error = True
        return self
    
    def row_count(self, n: Optional[int] = None, *, exact: Optional[int] = None,
                  min: Optional[int] = None, max: Optional[int] = None,
                  warn_only: bool = False) -> 'FrameCheck':
        if n is not None:
            if exact is not None or min is not None or max is not None:
                raise ValueError("If using row_count(n), do not also pass 'exact', 'min', or 'max'")
            exact = n
        self._dataframe_checks.append(
            RowCountCheck(exact=exact, min=min, max=max, raise_on_fail=not warn_only)
        )
        return self
    
    def unique(self, columns: Optional[List[str]] = None) -> 'FrameCheck':
        self._dataframe_checks.append(UniquenessCheck(columns=columns))
        return self


    def column(self, name: str, **kwargs) -> 'FrameCheck':
        if self._finalized:
            raise RuntimeError("Cannot call .column() after .only_defined_columns()")
        col_type = kwargs.pop('type', None)
        raise_on_fail = not kwargs.pop('warn_only', False)
        if col_type is None and not kwargs:
            self._column_checks.append(ColumnExistsCheck(name, raise_on_fail))
            return self
        
        if 'function' in kwargs:
            self._column_checks.append(CustomFunctionCheck(
                column_name=name,
                function=kwargs['function'],
                description=kwargs.get('description', ''),
                raise_on_fail=raise_on_fail
            ))
            return self
        
        checks = CheckFactory.create(
            col_type, column_name=name, raise_on_fail=raise_on_fail, **kwargs
        )
        if not isinstance(checks, list):
            checks = [checks]
        self._column_checks.extend(checks)
        return self

    def columns(self, names: List[str], **kwargs) -> 'FrameCheck':
        for name in names:
            self.column(name, **kwargs)
        return self

    def columns_are(self, expected_columns: List[str], warn_only: bool = False) -> 'FrameCheck':
        self.df_checks.append(ExactColumnsCheck(expected_columns, raise_on_fail=not warn_only))
        return self
    
    def custom_check(self, function, description: Optional[str] = None) -> 'FrameCheck':
        self._dataframe_checks.append(CustomCheck(function=function, description=description))
        return self

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        if self._finalized:
            expected_cols = [check.column_name for check in self._column_checks if hasattr(check, 'column_name')]
            self._dataframe_checks.append(DefinedColumnsOnlyCheck(expected_columns=expected_cols))

        errors = []
        warnings_list = []
        failing_indices = set()
        error_indices = set()

        for check in self._column_checks:
            if check.column_name not in df.columns:
                msg = f"Column '{check.column_name}' is missing."
                (errors if check.raise_on_fail else warnings_list).append(msg)
                continue
            result = check.validate(df[check.column_name])
            if result.get("messages"):
                if check.raise_on_fail:
                    errors.extend(result["messages"])
                    error_indices.update(result["failing_indices"])
                else:
                    warnings_list.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        for df_check in self._dataframe_checks:
            result = df_check.validate(df)
            if result.get("messages"):
                if df_check.raise_on_fail:
                    errors.extend(result["messages"])
                    error_indices.update(result["failing_indices"])
                else:
                    warnings_list.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        # Emit to user
        self._emit_warnings(warnings_list)
        
        result = ValidationResult(errors=errors, warnings=warnings_list, failing_row_indices=failing_indices)
        result._error_indices = error_indices
        
        if self._raise_on_error and errors:
            raise ValueError("FrameCheck validation failed:\n" + "\n".join(errors))
        else:
            self._emit_errors(errors)
        return result
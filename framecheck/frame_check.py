"""
frame_check.py

Validation engine for pandas DataFrames using composable column and DataFrame checks.

This module provides the core FrameCheck API, including Schema and ValidationResult
objects, that allow declarative data validation and rule chaining.
"""
import pandas as pd
from typing import List, Set, Optional, Dict, Any, Literal
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
    ColumnComparisonCheck,
    CustomCheck,
    DataFrameCheck,
    DefinedColumnsOnlyCheck,
    ExactColumnsCheck,
    IsEmptyCheck,
    NoNullsCheck,
    NotEmptyCheck,
    RowCountCheck,
    UniquenessCheck
)

from framecheck.utilities import CheckFactory




class FrameCheckWarning(UserWarning):
    """
    Custom warning class for FrameCheck validation.

    This warning is used to emit validation-related warnings during DataFrame
    checks. It inherits from the built-in UserWarning.
    """
    pass




class ValidationResult:
    """
    Represents the result of validating a DataFrame using FrameCheck.

    Attributes
    ----------
    errors : List[str]
        A list of error messages generated during validation.
    warnings : List[str]
        A list of warning messages generated during validation.
    _failing_row_indices : Set[int], optional
        Indices of rows in the DataFrame that failed validation.
    """
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
        """
        Indicates whether the validation passed without errors.

        Returns
        -------
        bool
            True if no errors were recorded, False otherwise.
        """
        return len(self.errors) == 0

    def get_invalid_rows(self, df: pd.DataFrame, include_warnings: bool = True) -> pd.DataFrame:
        """
        Retrieve rows from the DataFrame that failed validation.

        Parameters
        ----------
        df : pd.DataFrame
            The original DataFrame that was validated.
        include_warnings : bool, default=True
            If False, only rows with errors are included.

        Returns
        -------
        pd.DataFrame
            A subset of the original DataFrame with invalid rows.

        Raises
        ------
        ValueError
            If indices cannot be matched to the original DataFrame.
        """
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
        """
        Return a human-readable string summarizing the validation result.

        Returns
        -------
        str
            Summary of validation outcome, including counts of errors and warnings.
        """
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
        """
        Convert the validation result to a dictionary.

        Returns
        -------
        dict
            A dictionary containing 'is_valid', 'errors', and 'warnings'.
        """
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }




class Schema:
    """
    Represents a schema used to validate a DataFrame.

    Parameters
    ----------
    column_checks : List
        A list of column-level checks to apply.
    dataframe_checks : List
        A list of DataFrame-level checks to apply.

    Methods
    -------
    validate(df, verbose=False) -> ValidationResult
        Run all checks on the provided DataFrame and return the result.
    """
    def __init__(self, column_checks: List, dataframe_checks: List):
        self.column_checks = column_checks
        self.dataframe_checks = dataframe_checks

    def validate(self, df: pd.DataFrame, verbose: bool = False) -> ValidationResult:
        """
        Validate a DataFrame using the defined column and DataFrame checks.

        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame to validate.
        verbose : bool, default=False
            Currently unused.

        Returns
        -------
        ValidationResult
            Object containing error and warning messages from validation.
        """
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
    """
    A chainable interface for validating pandas DataFrames using both column-level
    and DataFrame-level checks.

    This class allows declarative construction of validation logic, with support for
    warnings, hard failures, and flexible rule definitions.

    Parameters
    ----------
    log_errors : bool, optional
        Whether to emit validation errors and warnings as runtime warnings.
    """
    def __init__(self, log_errors: bool = True):
        self._column_checks = []
        self._dataframe_checks = []
        self._finalized = False
        self._show_warnings = log_errors
        self._raise_on_error = False
        warnings.simplefilter('always', FrameCheckWarning)

    def _emit_warnings(self, warning_messages: List[str]):
        """
        Emit validation warnings using the FrameCheckWarning class.
    
        Parameters
        ----------
        warning_messages : list of str
            Warning messages to emit as a formatted multi-line warning.
        """
        if warning_messages:
            full_message = "\n".join(f"- {msg}" for msg in warning_messages)
            warnings.warn(f"FrameCheck validation warnings:\n{full_message}", FrameCheckWarning, stacklevel=3)
    
    def _emit_errors(self, error_messages: List[str]):
        """
        Emit validation errors as warnings if self._show_warnings is True.
    
        Parameters
        ----------
        error_messages : list of str
            Error messages to emit as a formatted multi-line warning.
        """
        if self._show_warnings and error_messages:
            full_message = "\n".join(f"- {msg}" for msg in error_messages)
            warnings.warn(f"FrameCheck validation errors:\n{full_message}", FrameCheckWarning, stacklevel=3)

    def empty(self) -> 'FrameCheck':
        """
        Add a check to ensure the DataFrame is empty.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._dataframe_checks.append(IsEmptyCheck())
        return self
    
    def not_empty(self) -> 'FrameCheck':
        """
        Add a check to ensure the DataFrame is not empty.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._dataframe_checks.append(NotEmptyCheck())
        return self
    
    def not_null(self, columns: Optional[List[str]] = None, warn_only: bool = False) -> 'FrameCheck':
        """
        Add a check to ensure specified columns have no null (NaN) values.
    
        Parameters
        ----------
        columns : list of str, optional
            Column names to check for null values. If None, all columns will be checked.
        warn_only : bool, optional
            If True, failures are treated as warnings instead of errors.
    
        Returns
        -------
        FrameCheck
            The updated FrameCheck instance with the null check added.
        """
        self._dataframe_checks.append(NoNullsCheck(columns=columns, raise_on_fail=not warn_only))
        return self
    
    def only_defined_columns(self) -> 'FrameCheck':
        """
        Restrict validation to only the explicitly defined columns.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._finalized = True
        return self
    
    def raise_on_error(self) -> 'FrameCheck':
        """
        Raise a ValueError if validation fails, instead of just returning the result.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._raise_on_error = True
        return self
    
    def row_count(self, n: Optional[int] = None, *, exact: Optional[int] = None,
                  min: Optional[int] = None, max: Optional[int] = None,
                  warn_only: bool = False) -> 'FrameCheck':
        """
        Add a row count check for the DataFrame.

        Parameters
        ----------
        n : int, optional
            Shortcut for exact row count.
        exact : int, optional
            Require exactly this many rows.
        min : int, optional
            Minimum number of rows allowed.
        max : int, optional
            Maximum number of rows allowed.
        warn_only : bool, optional
            If True, failures will be treated as warnings.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.

        Raises
        ------
        ValueError
            If `n` is used alongside `exact`, `min`, or `max`.
        """
        if n is not None:
            if exact is not None or min is not None or max is not None:
                raise ValueError("If using row_count(n), do not also pass 'exact', 'min', or 'max'")
            exact = n
        self._dataframe_checks.append(
            RowCountCheck(exact=exact, min=min, max=max, raise_on_fail=not warn_only)
        )
        return self
    
    def unique(self, columns: Optional[List[str]] = None) -> 'FrameCheck':
        """
        Add a uniqueness constraint on one or more columns.

        Parameters
        ----------
        columns : list of str, optional
            Columns that must contain unique combinations of values.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._dataframe_checks.append(UniquenessCheck(columns=columns))
        return self


    def column(self, name: str, **kwargs) -> 'FrameCheck':
        """
        Add validation rules for a single column.

        Parameters
        ----------
        name : str
            Name of the column.
        type : str, optional
            The expected data type (e.g., 'int', 'str', 'bool').
        warn_only : bool, optional
            If True, failures will be treated as warnings.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.

        Raises
        ------
        RuntimeError
            If called after `.only_defined_columns()` was set.
        """
        if self._finalized:
            raise RuntimeError("Cannot call .column() after .only_defined_columns()")
        col_type = kwargs.pop('type', None)
        raise_on_fail = not kwargs.pop('warn_only', False)
        if col_type is None and not kwargs:
            self._column_checks.append(ColumnExistsCheck(name, raise_on_fail))
            return self
        
        checks = CheckFactory.create(
            col_type, column_name=name, raise_on_fail=raise_on_fail, **kwargs
        )
        if not isinstance(checks, list):
            checks = [checks]
        self._column_checks.extend(checks)
        return self

    def columns(self, names: List[str], **kwargs) -> 'FrameCheck':
        """
        Apply the same column check logic to multiple columns.

        Parameters
        ----------
        names : list of str
            The column names to validate.
        **kwargs
            Additional keyword arguments passed to `column()`.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        for name in names:
            self.column(name, **kwargs)
        return self

    def columns_are(self, expected_columns: List[str], warn_only: bool = False) -> 'FrameCheck':
        """
        Require that the DataFrame contains only the specified columns in exact order.

        Parameters
        ----------
        expected_columns : list of str
            The expected column names.
        warn_only : bool, optional
            If True, mismatches are warnings instead of errors.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self.df_checks.append(ExactColumnsCheck(expected_columns, raise_on_fail=not warn_only))
        return self
    
    def compare(
        self,
        left_column: str,
        operator: Literal["<", "<=", "==", "!=", ">=", ">"],
        right_column: str,
        type: Optional[str] = None,
        description: Optional[str] = None,
        warn_only: bool = False
    ) -> 'FrameCheck':
        """
        Add a check comparing values between two columns.
    
        This method creates a validation rule that ensures values in one column
        have the specified relationship to values in another column. It's useful
        for validating business rules like "price > cost" or "end_date > start_date".
    
        Parameters
        ----------
        left_column : str
            Name of the first column to compare.
        operator : str
            Comparison operator: "<", "<=", "==", "!=", ">=", or ">".
        right_column : str
            Name of the second column to compare.
        type : str, optional
            Type of comparison to perform: 'numeric', 'string', 'datetime'.
            If not specified, will try to infer from column types.
        description : str, optional
            Custom description for the validation message.
        warn_only : bool, optional
            If True, failures are warnings instead of errors.
    
        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
    
        Examples
        --------
        >>> schema = (FrameCheck()
        ...     .column('price', type='float')
        ...     .column('cost', type='float')
        ...     .compare('price', '>', 'cost')
        ...     .not_null()
        ... )
        
        >>> # With date comparison and custom error
        >>> schema = (FrameCheck()
        ...     .column('start_date', type='datetime')
        ...     .column('end_date', type='datetime')
        ...     .compare('end_date', '>', 'start_date',
        ...             type='datetime',
        ...             description="End date must be after start date")
        ... )
        """
        self._dataframe_checks.append(
            ColumnComparisonCheck(
                left_column=left_column,
                operator=operator,
                right_column=right_column,
                comparison_type=type,
                description=description,
                raise_on_fail=not warn_only
            )
        )
        return self
    
    
    def custom_check(self, function, description: Optional[str] = None) -> 'FrameCheck':
        """
        Add a custom user-defined validation function.

        Parameters
        ----------
        function : Callable[[pd.DataFrame], dict]
            A function that returns a dict with 'messages' and 'failing_indices'.
        description : str, optional
            Description of the custom check.

        Returns
        -------
        FrameCheck
            The updated FrameCheck instance.
        """
        self._dataframe_checks.append(CustomCheck(function=function, description=description))
        return self

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Run all defined checks against the provided DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame to validate.

        Returns
        -------
        ValidationResult
            The result of the validation process.

        Raises
        ------
        ValueError
            If `raise_on_error()` was set and validation fails.
        """
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
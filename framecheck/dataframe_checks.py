"""
dataframe_checks.py

Validation rules applied at the DataFrame level.
Each check subclass implements a `validate()` method returning validation messages
and optionally failing row indices.
"""

import pandas as pd
from typing import Optional, List, Dict, Set
from framecheck.function_registry import is_registered, get_registry_name, get_registered_function


class DataFrameCheck:
    """
    Base class for all DataFrame-level validation checks.

    Parameters
    ----------
    raise_on_fail : bool
        If True, failing the check is treated as an error. Otherwise, it's a warning.
    """
    def __init__(self, raise_on_fail: bool = True):
        self.raise_on_fail = raise_on_fail

    def validate(self, df: pd.DataFrame) -> Dict[str, object]:
        """
        Validate the DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        dict
            A dict with keys 'messages' and 'failing_indices'.

        Raises
        ------
        NotImplementedError
            If not overridden by subclass.
        """
        raise NotImplementedError("Subclasses must implement validate()")


class ColumnComparisonCheck(DataFrameCheck):
    """
    Check that compares values between two columns using specified operators.

    This check validates that the relationship between values in two columns
    satisfies the specified comparison operator. It supports numeric, string,
    and datetime comparisons with type inference or explicit type specification.

    Parameters
    ----------
    left_column : str
        Name of the first column to compare.
    operator : str
        Comparison operator: "<", "<=", "==", "!=", ">=", or ">".
    right_column : str
        Name of the second column to compare.
    comparison_type : str, optional
        Type of comparison to perform: 'numeric', 'string', 'datetime'.
        If not specified, will attempt to infer from column types.
    description : str, optional
        Custom description for validation failures.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.

    Examples
    --------
    >>> check = ColumnComparisonCheck('price', '>', 'cost')
    >>> result = check.validate(df)
    
    >>> # With explicit type and custom message
    >>> check = ColumnComparisonCheck('end_date', '>', 'start_date', 
    ...                               comparison_type='datetime',
    ...                               description="End date must be after start date")
    """
    def __init__(
        self,
        left_column: str,
        operator: str,
        right_column: str,
        comparison_type: Optional[str] = None,
        description: Optional[str] = None,
        raise_on_fail: bool = True
    ):
        super().__init__(raise_on_fail)
        self.left_column = left_column
        self.operator = operator
        self.right_column = right_column
        self.comparison_type = comparison_type

        # Define supported operators
        self.operators = {
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">=": lambda a, b: a >= b,
            ">": lambda a, b: a > b
        }

        if operator not in self.operators:
            raise ValueError(f"Operator must be one of: {', '.join(self.operators.keys())}")

        self.description = description or f"Column '{left_column}' must be {operator} column '{right_column}'"

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate the column comparison constraint.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        dict
            Dictionary with 'messages' and 'failing_indices'.
        """
        messages = []
        failing_indices = set()

        # First check if both columns exist
        if self.left_column not in df.columns:
            messages.append(f"Column '{self.left_column}' does not exist for comparison.")
            return {"messages": messages, "failing_indices": failing_indices}

        if self.right_column not in df.columns:
            messages.append(f"Column '{self.right_column}' does not exist for comparison.") #nocov
            return {"messages": messages, "failing_indices": failing_indices} #nocov

        # Determine comparison type if not explicitly provided
        comparison_type = self.comparison_type

        if not comparison_type:
            # Look at column dtypes to infer comparison type
            left_dtype = str(df[self.left_column].dtype)
            right_dtype = str(df[self.right_column].dtype)
            
            if 'datetime' in left_dtype or 'datetime' in right_dtype:
                comparison_type = 'datetime' #nocov
            elif ('int' in left_dtype and 'int' in right_dtype) or \
                 ('float' in left_dtype and 'float' in right_dtype) or \
                 ('int' in left_dtype and 'float' in right_dtype) or \
                 ('float' in left_dtype and 'int' in right_dtype):
                comparison_type = 'numeric'

        # Apply the comparison row by row
        for idx, row in df.iterrows():
            left_val = row[self.left_column]
            right_val = row[self.right_column]

            # Handle null values
            if pd.isna(left_val) or pd.isna(right_val):
                failing_indices.add(idx)
                continue

            # Apply type-specific handling
            if comparison_type == 'datetime':
                try:
                    left_val = pd.to_datetime(left_val)
                    right_val = pd.to_datetime(right_val)
                except (ValueError, TypeError):
                    failing_indices.add(idx)
                    continue
            elif comparison_type == 'numeric':
                try:
                    left_val = float(left_val)
                    right_val = float(right_val)
                except (ValueError, TypeError):
                    failing_indices.add(idx)
                    continue

            # Perform the comparison
            try:
                if not self.operators[self.operator](left_val, right_val):
                    failing_indices.add(idx)
            except TypeError:#nocov
                failing_indices.add(idx)#nocov

        if failing_indices:
            messages.append(f"{self.description} (failed on {len(failing_indices)} row(s))")
        return {"messages": messages, "failing_indices": failing_indices}


class CustomCheck(DataFrameCheck):
    """
    User-defined custom validation function.

    Parameters
    ----------
    function : Callable
        A function that returns True for valid rows, False otherwise.
    description : str, optional
        Message to include in case of failure.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, function, description: Optional[str] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.function = function
        self.description = description or "Custom check failed"
        self.registry_name = get_registry_name(function) if is_registered(function) else None

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Apply the custom function to each row in the DataFrame.

        Returns
        -------
        dict
            Dict with messages and failing row indices.
        """
        messages = []
        failing_indices = set()

        invalid_mask = ~df.apply(self.function, axis=1)
        if invalid_mask.any():
            failing_indices = df[invalid_mask].index
            messages.append(f"{self.description} (failed on {len(failing_indices)} row(s))")

        return {"messages": messages, "failing_indices": set(failing_indices)}


class DefinedColumnsOnlyCheck(DataFrameCheck):
    """
    Ensure that the DataFrame contains only the expected columns.

    Parameters
    ----------
    expected_columns : list of str
        Columns that are allowed.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, expected_columns: List[str], raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.expected_columns = set(expected_columns)
        
    @staticmethod
    def _serialize_defined_columns_check(check) -> dict:
        """Serialize DefinedColumnsOnlyCheck."""
        result = {}
        if hasattr(check, "expected_columns"):
            result["expected_columns"] = list(check.expected_columns)
        return result

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate presence of only expected columns.

        Returns
        -------
        dict
            Dict with messages and empty index set.
        """
        actual = set(df.columns)
        extra = actual - self.expected_columns
        messages = []
        if extra:
            messages.append(f"Unexpected columns in DataFrame: {sorted(extra)}")
        return {"messages": messages, "failing_indices": set()}


class ExactColumnsCheck(DataFrameCheck):
    """
    Ensure the DataFrame has exactly the specified columns in order.

    Parameters
    ----------
    expected_columns : list of str
        Required column names in the correct order.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, expected_columns: List[str], raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.expected_columns = expected_columns

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate exact match of column names and order.

        Returns
        -------
        dict
            Dict with messages and empty index set.
        """
        actual_columns = list(df.columns)
        messages = []
        failing_indices = set()

        expected_set = set(self.expected_columns)
        actual_set = set(actual_columns)

        missing = expected_set - actual_set
        extra = actual_set - expected_set

        if missing:
            messages.append(f"Missing column(s): {sorted(missing)}.")

        if extra:
            messages.append(f"Unexpected column(s): {sorted(extra)}.")

        if not missing and not extra and actual_columns != self.expected_columns:
            messages.append(
                f"Column order mismatch: expected {self.expected_columns}, "
                f"but got {actual_columns}."
            )

        return {"messages": messages, "failing_indices": failing_indices}


class NotEmptyCheck(DataFrameCheck):
    """
    Ensure that the DataFrame is not empty.

    Parameters
    ----------
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)

    def validate(self, df: pd.DataFrame) -> dict:
        messages = []
        if df.empty:
            messages.append("DataFrame is unexpectedly empty.")
        return {"messages": messages, "failing_indices": set()}


class IsEmptyCheck(DataFrameCheck):
    """
    Ensure that the DataFrame is empty.

    Parameters
    ----------
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate that the DataFrame is empty.

        Returns
        -------
        dict
            Dict with message and empty index set if failed.
        """
        messages = []
        if not df.empty:
            messages.append("DataFrame is unexpectedly non-empty.")
        return {"messages": messages, "failing_indices": set()}


class NoNullsCheck(DataFrameCheck):
    """
    Check that no nulls exist in specified or all columns.

    Parameters
    ----------
    columns : list of str, optional
        Columns to validate for nulls. If None, all columns are checked.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, columns: Optional[List[str]] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.columns = columns

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate that specified columns do not contain nulls.

        Returns
        -------
        dict
            Dict with messages and failing row indices.
        """
        cols_to_check = self.columns or df.columns.tolist()
        messages = []
        failing_indices = set()

        for col in cols_to_check:
            if df[col].isna().any():
                messages.append(f"Column '{col}' contains null values.")
                failing_indices.update(df[df[col].isna()].index)

        return {"messages": messages, "failing_indices": failing_indices}


class UniquenessCheck(DataFrameCheck):
    """
    Ensure rows (or combinations of specified columns) are unique.

    Parameters
    ----------
    columns : list of str, optional
        Columns to enforce uniqueness on. If None, all columns are used.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    """
    def __init__(self, columns: Optional[List[str]] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.columns = columns

    def validate(self, df: pd.DataFrame) -> Dict[str, object]:
        """
        Validate uniqueness of rows or column combinations.

        Returns
        -------
        dict
            Dict with messages and failing row indices.
        """
        messages = []
        failing_indices: Set[int] = set()

        if self.columns:
            missing = [col for col in self.columns if col not in df.columns]
            if missing:
                messages.append(f"Missing columns for uniqueness check: {missing}")
                return {"messages": messages, "failing_indices": failing_indices}

            duplicates = df[df.duplicated(subset=self.columns)]
            if not duplicates.empty:
                messages.append(f"Rows are not unique based on columns: {self.columns}")
                failing_indices.update(duplicates.index)
        else:
            duplicates = df[df.duplicated()]
            if not duplicates.empty:
                messages.append("DataFrame contains duplicate rows.")
                failing_indices.update(duplicates.index)

        return {"messages": messages, "failing_indices": failing_indices}


class RowCountCheck(DataFrameCheck):
    """
    Enforce row count constraints on a DataFrame.

    Parameters
    ----------
    exact : int, optional
        Require exactly this number of rows.
    min : int, optional
        Minimum number of rows.
    max : int, optional
        Maximum number of rows.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.

    Raises
    ------
    ValueError
        If both 'exact' and ('min' or 'max') are provided.
    """
    def __init__(
        self,
        exact: Optional[int] = None,
        min: Optional[int] = None,
        max: Optional[int] = None,
        raise_on_fail: bool = True
    ):
        super().__init__(raise_on_fail)
        self.exact = exact
        self.min = min
        self.max = max

        if self.exact is not None and (self.min is not None or self.max is not None):
            raise ValueError("Specify either 'exact' OR 'min'/'max', not both.")

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Validate that the row count meets specified constraints.

        Returns
        -------
        dict
            Dict with messages and empty failing index set.
        """
        messages = []
        row_count = len(df)

        if self.exact is not None and row_count != self.exact:
            messages.append(
                f"DataFrame must have exactly {self.exact} rows (found {row_count})."
            )

        if self.min is not None and row_count < self.min:
            messages.append(
                f"DataFrame must have at least {self.min} rows (found {row_count})."
            )

        if self.max is not None and row_count > self.max:
            messages.append(
                f"DataFrame must have at most {self.max} rows (found {row_count})."
            )
        return {"messages": messages, "failing_indices": set()}

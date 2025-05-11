"""
column_checks.py

Validation rules applied at the column level. Each subclass of ColumnCheck
implements logic specific to a data type or validation strategy.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import numbers
import numpy as np
import pandas as pd
from typing import Any, Callable, List, Optional, Union
from framecheck.utilities import CheckFactory


class ColumnCheck:
    """
    Base class for all column-level validation checks.

    Parameters
    ----------
    column_name : str
        The name of the column to validate.
    raise_on_fail : bool, optional
        Whether to treat validation failure as an error (default is True).
    not_null : bool, optional
        Whether to fail if the column contains null values (default is False).
    """
    def __init__(self, column_name: str, raise_on_fail: bool = True, not_null: bool = False):
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail
        self.not_null = not_null

    def validate(self, series: pd.Series) -> dict:
        """
        Perform validation on the given pandas Series.

        Parameters
        ----------
        series : pd.Series
            The column data to validate.

        Returns
        -------
        dict
            Dictionary with 'messages' and 'failing_indices'.

        Raises
        ------
        NotImplementedError
            Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses should implement validate()")
        
    def _check_membership_constraints(
        self,
        series: pd.Series,
        in_set: Optional[List[Any]] = None,
        not_in_set: Optional[List[Any]] = None,
        equals_value: Optional[Any] = None
    ) -> dict:
        """
        Helper to check if values are in an allowed set, not in a disallowed set,
        or equal to a fixed value.

        Parameters
        ----------
        series : pd.Series
            The data to validate.
        in_set : list, optional
            Allowed values.
        not_in_set : list, optional
            Disallowed values.
        equals_value : any, optional
            A value all entries must match.

        Returns
        -------
        dict
            Dictionary with 'messages' and 'failing_indices'.
        """
        messages = []
        failing_indices = set()
    
        if equals_value is not None:
            mask = series != equals_value
            invalid_values = series[mask].dropna()
            if not invalid_values.empty:
                sample = list(invalid_values.unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' must equal '{equals_value}', but found: {sample}."
                )
                failing_indices.update(invalid_values.index)
    
        elif in_set is not None:
            mask = ~series.isin(in_set)
            invalid_values = series[mask].dropna()
            if not invalid_values.empty:
                sample = list(invalid_values.unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' contains unexpected values: {sample}."
                )
                failing_indices.update(invalid_values.index)
    
        if not_in_set is not None:
            mask = series.isin(not_in_set)
            disallowed_values = series[mask].dropna()
            if not disallowed_values.empty:
                sample = list(disallowed_values.unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' contains disallowed values: {sample}."
                )
                failing_indices.update(disallowed_values.index)
    
        return {"messages": messages, "failing_indices": failing_indices}



class ColumnExistsCheck(ColumnCheck):
    """
    Dummy check used to assert column presence only.

    This check always passes and is used when you want to ensure that a column
    exists without enforcing any additional constraints.
    """
    def validate(self, series: pd.Series) -> dict:
        return {"messages": [], "failing_indices": set()}  # pragma: no cover


@CheckFactory.register('bool')
class BoolColumnCheck(ColumnCheck):
    """
    Validate that a column contains only boolean values.

    Parameters
    ----------
    column_name : str
        Name of the column to validate.
    equals : bool, optional
        If provided, asserts that all non-null values equal this boolean.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    not_null : bool, optional
        Whether the column must not contain nulls.
    """
    def __init__(self, column_name: str, equals: Optional[bool] = None, raise_on_fail: bool = True, not_null: bool = False):
        super().__init__(column_name, raise_on_fail, not_null)
        if equals is not None and not isinstance(equals, bool):
            raise ValueError(f"'equals' for boolean column '{column_name}' must be True or False, not {type(equals).__name__}")
        self._equals_value = equals

    def validate(self, series: pd.Series) -> dict:
        """
        Validate the Series for boolean type compliance and equality constraint.

        Parameters
        ----------
        series : pd.Series
            Column values to validate.

        Returns
        -------
        dict
            Dictionary with 'messages' and 'failing_indices'.
        """
        messages = []
        failing_indices = set()

        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        invalid_values = series[~series.map(lambda x: isinstance(x, bool)) & series.notna()]
        if not invalid_values.empty:
            sample = list(invalid_values.unique()[:3])
            messages.append(f"Column '{self.column_name}' contains non-boolean values: {sample}.")
            failing_indices.update(invalid_values.index)

        result = self._check_membership_constraints(
            series,
            equals_value=self._equals_value
        )
        messages.extend(result["messages"])
        failing_indices.update(result["failing_indices"])

        return {"messages": messages, "failing_indices": failing_indices}



@CheckFactory.register('datetime')
class DatetimeColumnCheck(ColumnCheck):
    """
    Validate that a column contains datetime values and optionally meets bounds.

    Parameters
    ----------
    column_name : str
        Name of the column to validate.
    min : str or datetime, optional
        Minimum allowed datetime value.
    max : str or datetime, optional
        Maximum allowed datetime value.
    before : str or datetime, optional
        All values must be before this datetime.
    after : str or datetime, optional
        All values must be after this datetime.
    equals : str or datetime, optional
        All values must match this datetime.
    format : str, optional
        Format string for parsing if input values are strings.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    not_null : bool, optional
        Whether the column must not contain nulls.

    Raises
    ------
    ValueError
        If 'equals' is used with any other bounds.
    """
    def __init__(
        self,
        column_name: str,
        min: Optional[str] = None,
        max: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        equals: Optional[str] = None,
        format: Optional[str] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.format = format

        def resolve_bound(value: Optional[Union[str, datetime]], bound_name: str) -> Optional[datetime]:
            """
        Convert a string or datetime input into a standardized datetime object.
    
        Recognizes natural language strings like 'today', 'now', 'yesterday', and 'tomorrow',
        or attempts to parse strings using the provided format or pandas fallback.
    
        Parameters
        ----------
        value : str or datetime, optional
            The boundary value to resolve.
        bound_name : str
            Name of the parameter being resolved (used in error messages).
    
        Returns
        -------
        datetime or None
            A parsed datetime object, or None if the input was None.
    
        Raises
        ------
        ValueError
            If parsing fails using the provided format.
        TypeError
            If the input is not a string or datetime.
        """
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower == 'today':
                    return datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
                elif value_lower == 'now':
                    return datetime.now()
                elif value_lower == 'yesterday':
                    return (datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                elif value_lower == 'tomorrow':
                    return (datetime.today() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                elif self.format:
                    try:
                        return datetime.strptime(value, self.format)
                    except ValueError:
                        raise ValueError(f"Failed to parse {bound_name}='{value}' using format='{self.format}'")
                else:
                    return pd.to_datetime(value)
            raise TypeError(f"{bound_name} must be a string or datetime, not {type(value)}")

        if equals is not None and any([min, max, before, after]):
            raise ValueError("Cannot specify 'equals' with any of 'min', 'max', 'before', or 'after'.")

        self._equals_value = resolve_bound(equals, "equals") if equals else None
        self.min = pd.to_datetime(min) if min else None
        self.max = pd.to_datetime(max) if max else None
        self.before = resolve_bound(before, "before")
        self.after = resolve_bound(after, "after")

    def validate(self, series: pd.Series) -> dict:
        """
        Validate that the column contains valid datetime values and respects defined constraints.
    
        Parameters
        ----------
        series : pd.Series
            The Series containing the column data to validate.
    
        Returns
        -------
        dict
            A dictionary with two keys:
            - 'messages': a list of validation error messages.
            - 'failing_indices': a set of row indices where validation failed.
    
        Raises
        ------
        ValueError
            If datetime conversion fails using the specified format.
        """
        messages = []
        failing_indices = set()

        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        try:
            coerced = pd.to_datetime(series, format=self.format, errors='coerce')
        except Exception:
            raise ValueError(f"Could not coerce values in '{self.column_name}' using format='{self.format}'")

        invalid_mask = coerced.isna() & series.notna()
        if invalid_mask.any():
            sample = list(series[invalid_mask].unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains values that are not valid dates: {sample}."
            )
            failing_indices.update(series[invalid_mask].index)

        non_null = series[series.notna()]
        types = non_null.map(type).unique()
        if len(types) > 1:
            messages.append(
                f"Column '{self.column_name}' contains inconsistent datetime types: {[t.__name__ for t in types[:3]]}."
            )

        if self._equals_value is not None:
            mask = coerced != self._equals_value
            mask |= invalid_mask
            if mask.any():
                sample = list(series[mask].unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' must equal {self._equals_value.date()}, but found: {sample}."
                )
                failing_indices.update(series[mask].index)
        else:
            bounds = [
                ('min', self.min, lambda x: x < self.min),
                ('max', self.max, lambda x: x > self.max),
                ('before', self.before, lambda x: x > self.before),
                ('after', self.after, lambda x: x < self.after),
            ]

            for label, bound, condition in bounds:
                if bound is not None:
                    mask = condition(coerced) | invalid_mask
                    if mask.any():
                        bound_label = bound.date() if hasattr(bound, "date") else bound
                        messages.append(f"Column '{self.column_name}' violates '{label}' constraint: {bound_label}.")
                        failing_indices.update(series[mask].index)

        return {"messages": messages, "failing_indices": failing_indices}
    

@CheckFactory.register('float')
class FloatColumnCheck(ColumnCheck):
    """
    Validate that a column contains numeric float-like values.

    Parameters
    ----------
    column_name : str
        Name of the column to validate.
    min : float, optional
        Minimum value allowed.
    max : float, optional
        Maximum value allowed.
    in_set : list of float, optional
        Allowed values.
    not_in_set : list of float, optional
        Disallowed values.
    equals : float, optional
        All values must equal this float.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    not_null : bool, optional
        Whether the column must not contain nulls.

    Raises
    ------
    ValueError
        If both 'in_set' and 'equals' are provided.
    """
    def __init__(
        self,
        column_name: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
        in_set: Optional[List[float]] = None,
        not_in_set: Optional[List[float]] = None,
        equals: Optional[float] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.min = min
        self.max = max
        self.not_in_set = not_in_set

        if equals is not None:
            if in_set is not None:
                raise ValueError("Cannot specify both 'in_set' and 'equals'")
            self.in_set = [equals]
            self._equals_value = equals
        else:
            self.in_set = in_set
            self._equals_value = None

    def validate(self, series: pd.Series) -> dict:
        """
        Validate that a column contains integer-like values.
    
        Parameters
        ----------
        column_name : str
            Name of the column to validate.
        min : int, optional
            Minimum value allowed.
        max : int, optional
            Maximum value allowed.
        in_set : list of int, optional
            Allowed values.
        not_in_set : list of int, optional
            Disallowed values.
        equals : int, optional
            All values must equal this integer.
        raise_on_fail : bool, optional
            Whether failure raises an error or warning.
        not_null : bool, optional
            Whether the column must not contain nulls.
    
        Raises
        ------
        ValueError
            If both 'in_set' and 'equals' are provided.
        """
        messages = []
        failing_indices = set()

        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        valid_numeric_types = (int, float, Decimal, numbers.Real)
        non_float_like = series[~series.map(lambda x: isinstance(x, valid_numeric_types) or pd.isna(x))]

        if not non_float_like.empty:
            sample = list(non_float_like.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains values that are not numeric: {sample}."
            )
            failing_indices.update(non_float_like.index)

        if non_float_like.index.equals(series.dropna().index):
            return {"messages": messages, "failing_indices": failing_indices}

        numeric_series = series.drop(index=non_float_like.index)

        result = self._check_membership_constraints(
            numeric_series,
            in_set=self.in_set,
            not_in_set=self.not_in_set,
            equals_value=self._equals_value
        )
        messages.extend(result["messages"])
        failing_indices.update(result["failing_indices"])

        inf_mask = numeric_series.map(lambda x: isinstance(x, float) and np.isinf(x))
        if inf_mask.any():
            messages.append(f"Column '{self.column_name}' contains infinite values.")
            failing_indices.update(numeric_series[inf_mask].index)

        if self.min is not None:
            min_mask = numeric_series < self.min
            if min_mask.any():
                messages.append(f"Column '{self.column_name}' has values less than {self.min}.")
                failing_indices.update(min_mask[min_mask].index)

        if self.max is not None:
            max_mask = numeric_series > self.max
            if max_mask.any():
                messages.append(f"Column '{self.column_name}' has values greater than {self.max}.")
                failing_indices.update(max_mask[max_mask].index)

        return {"messages": messages, "failing_indices": failing_indices}



@CheckFactory.register('int')
class IntColumnCheck(ColumnCheck):
    """
    Validate that a column contains string values, optionally matching regex or sets.

    Parameters
    ----------
    column_name : str
        Name of the column to validate.
    regex : str, optional
        A regular expression that all string values must match.
    in_set : list of str, optional
        Allowed values.
    not_in_set : list of str, optional
        Disallowed values.
    equals : str, optional
        All values must equal this string.
    raise_on_fail : bool, optional
        Whether failure raises an error or warning.
    not_null : bool, optional
        Whether the column must not contain nulls.

    Raises
    ------
    ValueError
        If both 'in_set' and 'equals' are provided.
    """
    def __init__(
        self,
        column_name: str,
        min: Optional[int] = None,
        max: Optional[int] = None,
        in_set: Optional[List[int]] = None,
        not_in_set: Optional[List[str]] = None,
        equals: Optional[int] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.min = min
        self.max = max
        self.not_in_set = not_in_set
        if equals is not None:
            if in_set is not None:
                raise ValueError("Cannot specify both 'in_set' and 'equals'")
            if not isinstance(equals, int):  # Check if equals is an integer
                raise ValueError("'equals' must be an integer.")
            self.in_set = [equals]
            self._equals_value = equals
        else:
            self.in_set = in_set
            self._equals_value = None

    def validate(self, series: pd.Series) -> dict:
        """
        Validate that the column contains integer-like values and meets constraints.
    
        Parameters
        ----------
        series : pd.Series
            The column to validate.
    
        Returns
        -------
        dict
            Dictionary with:
            - 'messages': list of validation failure descriptions
            - 'failing_indices': set of indices in the Series that failed validation
    
        Notes
        -----
        This method:
        - Accepts ints, and floats that represent integers (e.g., 5.0)
        - Rejects floats with decimals, booleans, strings, and infinite values
        - Enforces optional constraints like min, max, exact equality, and membership
        """
        messages = []
        failing_indices = set()
        
        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        def is_integer_like(x):
            if pd.isna(x):
                return True
            if isinstance(x, float) and np.isinf(x):
                return False
            if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
                return True
            if isinstance(x, float) and x.is_integer():
                return True
            return False

        invalid = series[~series.map(is_integer_like)]

        inf_values = invalid[invalid.map(lambda x: isinstance(x, float) and np.isinf(x))]
        if not inf_values.empty:
            messages.append(f"Column '{self.column_name}' contains infinite values.")

        if not invalid.empty:
            sample = list(invalid.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains values that are not integer-like (e.g., decimals or strings): {sample}."
            )
            failing_indices.update(invalid.index)

        if invalid.index.equals(series.dropna().index):
            return {"messages": messages, "failing_indices": failing_indices}

        valid_series = series.drop(index=invalid.index)

        if self.min is not None:
            mask = valid_series < self.min
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values less than {self.min}.")
                failing_indices.update(mask[mask].index)

        if self.max is not None:
            mask = valid_series > self.max
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values greater than {self.max}.")
                failing_indices.update(mask[mask].index)

        result = self._check_membership_constraints(
            valid_series,
            in_set=self.in_set,
            not_in_set=self.not_in_set,
            equals_value=self._equals_value
        )
        messages.extend(result["messages"])
        failing_indices.update(result["failing_indices"])

        return {"messages": messages, "failing_indices": failing_indices}



@CheckFactory.register('string')
class StringColumnCheck(ColumnCheck):
    """
    Validate that a column contains string values and optionally matches regex or value constraints.
    
    This check supports ensuring all values match a regular expression pattern, belong to
    an allowed set, are excluded from a disallowed set, or equal a specific string.
    
    Parameters
    ----------
    column_name : str
        Name of the column to validate.
    regex : str, optional
        Regular expression that all values must match.
    in_set : list of str, optional
        Allowed string values.
    not_in_set : list of str, optional
        Disallowed string values.
    equals : str, optional
        All values must equal this string exactly.
    raise_on_fail : bool, optional
        Whether to treat validation failures as errors (default is True).
    not_null : bool, optional
        Whether to fail if the column contains nulls.
        
    Raises
    ------
    ValueError
        If both 'in_set' and 'equals' are provided.
    """
    def __init__(
        self, 
        column_name: str, 
        regex: Optional[str] = None, 
        in_set: Optional[List[str]] = None,
        not_in_set: Optional[List[str]] = None,
        equals: Optional[str] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.regex = regex

        if equals is not None and in_set is not None:
            raise ValueError("Cannot specify both 'in_set' and 'equals'")

        self.in_set = in_set
        self._equals_value = equals
        self.not_in_set = not_in_set

    def validate(self, series: pd.Series) -> dict:
        """
        Validate the column's values against string constraints.
    
        Parameters
        ----------
        series : pd.Series
            The column to validate.
    
        Returns
        -------
        dict
            A dictionary with:
            - 'messages': list of validation failure messages
            - 'failing_indices': set of indices where validation failed
    
        Notes
        -----
        This method:
        - Validates type compatibility with strings
        - Optionally applies a regex pattern match
        - Optionally checks for equality, inclusion, and exclusion rules
        - Supports null checks if enabled
        """
        messages = []
        failing_indices = set()

        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        if self.regex:
            non_null = series[series.notna()]
            failed = non_null.astype(str)[~non_null.astype(str).str.match(self.regex)]
            if not failed.empty:
                sample = list(failed.unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' has values not matching regex '{self.regex}': {sample}."
                )
                failing_indices.update(failed.index)

        result = self._check_membership_constraints(
            series,
            in_set=self.in_set,
            not_in_set=self.not_in_set,
            equals_value=self._equals_value
        )
        messages.extend(result["messages"])
        failing_indices.update(result["failing_indices"])

        return {"messages": messages, "failing_indices": failing_indices}

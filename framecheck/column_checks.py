from datetime import datetime, timedelta
from decimal import Decimal
import numbers
import numpy as np
import pandas as pd
from typing import Any, Callable, List, Optional, Union
from framecheck.utilities import CheckFactory


class ColumnCheck:
    def __init__(self, column_name: str, raise_on_fail: bool = True, not_null: bool = False):
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail
        self.not_null = not_null

    def validate(self, series: pd.Series) -> dict:
        raise NotImplementedError("Subclasses should implement validate()")


class ColumnExistsCheck(ColumnCheck):
    def validate(self, series: pd.Series) -> dict:
        return {"messages": [], "failing_indices": set()}  # pragma: no cover


@CheckFactory.register('bool')
class BoolColumnCheck(ColumnCheck):
    def __init__(
        self,
        column_name: str,
        equals: Optional[bool] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)

        if equals is not None and not isinstance(equals, bool):
            raise ValueError(f"'equals' for boolean column '{column_name}' must be True or False, not {type(equals).__name__}")

        self._equals_value = equals

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()
        
        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        # Check for non-boolean values
        invalid_values = series[~series.map(lambda x: isinstance(x, bool)) & series.notna()]
        if not invalid_values.empty:
            sample = list(invalid_values.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains non-boolean values: {sample}."
            )
            failing_indices.update(invalid_values.index)

        # Check for equality condition if 'equals' is set
        if self._equals_value is not None:
            equals_mask = series != self._equals_value
            if equals_mask.any():
                messages.append(f"Column '{self.column_name}' contains values that must equal {self._equals_value}.")
                failing_indices.update(equals_mask[equals_mask].index)

        return {"messages": messages, "failing_indices": failing_indices}


@CheckFactory.register('datetime')
class DatetimeColumnCheck(ColumnCheck):
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
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail
        self.not_null = not_null
        self.format = format

        def resolve_bound(value: Optional[Union[str, datetime]], bound_name: str) -> Optional[datetime]:
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

        # Validate no conflict between equals and other bounds
        if equals is not None and any([min, max, before, after]):
            raise ValueError("Cannot specify 'equals' with any of 'min', 'max', 'before', or 'after'.")

        self._equals_value = resolve_bound(equals, "equals") if equals else None
        self.min = pd.to_datetime(min) if min else None
        self.max = pd.to_datetime(max) if max else None
        self.before = resolve_bound(before, "before")
        self.after = resolve_bound(after, "after")

    def validate(self, series: pd.Series) -> dict:
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
    def __init__(
        self,
        column_name: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
        in_set: Optional[List[float]] = None,
        equals: Optional[float] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.min = min
        self.max = max
        self.in_set = in_set
        
        if equals is not None:
            if in_set is not None:
                raise ValueError("Cannot specify both 'in_set' and 'equals'")
            self.in_set = [equals]
            self._equals_value = equals
        else:
            self.in_set = in_set
            self._equals_value = None

    def validate(self, series: pd.Series) -> dict:
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
    
        if self.in_set is not None:
            mask = ~numeric_series.isin(self.in_set)
            if mask.any():
                bad_values = [v.item() if hasattr(v, 'item') else v for v in numeric_series[mask].unique()[:3]]
                messages.append(f"Column '{self.column_name}' contains values not in allowed set: {bad_values}.")
                failing_indices.update(mask[mask].index)
    
        # Check for equality condition
        if self._equals_value is not None:
            equals_mask = numeric_series != self._equals_value
            if equals_mask.any():
                messages.append(f"Column '{self.column_name}' contains values that must equal {self._equals_value}.")
                failing_indices.update(equals_mask[equals_mask].index)
    
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
    def __init__(
        self,
        column_name: str,
        min: Optional[int] = None,
        max: Optional[int] = None,
        in_set: Optional[List[int]] = None,
        equals: Optional[int] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.min = min
        self.max = max

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

        if self.in_set is not None:
            mask = ~valid_series.isin(self.in_set)
            if mask.any():
                bad_values = [v.item() if hasattr(v, 'item') else v for v in valid_series[mask].unique()[:3]]
                if self._equals_value is not None:
                    messages.append(
                        f"Column '{self.column_name}' must equal {self._equals_value}, but found values: {bad_values}."
                    )
                else:
                    messages.append(
                        f"Column '{self.column_name}' contains values not in allowed set: {bad_values}."
                    )
                failing_indices.update(mask[mask].index)

        return {"messages": messages, "failing_indices": failing_indices}



@CheckFactory.register('string')
class StringColumnCheck(ColumnCheck):
    def __init__(
        self, 
        column_name: str, 
        regex: Optional[str] = None, 
        in_set: Optional[List[str]] = None,
        equals: Optional[str] = None,
        raise_on_fail: bool = True,
        not_null: bool = False
    ):
        super().__init__(column_name, raise_on_fail, not_null)
        self.regex = regex

        if equals is not None:
            if in_set is not None:
                raise ValueError("Cannot specify both 'in_set' and 'equals'")
            self.in_set = [equals]
            self._equals_value = equals
        else:
            self.in_set = in_set
            self._equals_value = None

    def validate(self, series: pd.Series) -> dict:
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

        if self.in_set:
            mask = ~series.isin(self.in_set)
            invalid_values = series[mask].dropna()
            if not invalid_values.empty:
                sample = list(invalid_values.unique()[:3])
                if self._equals_value is not None:
                    messages.append(
                        f"Column '{self.column_name}' must equal '{self._equals_value}', but found: {sample}."
                    )
                else:
                    messages.append(
                        f"Column '{self.column_name}' contains unexpected values: {sample}."
                    )
                failing_indices.update(invalid_values.index)

        return {"messages": messages, "failing_indices": failing_indices}




class CustomFunctionCheck(ColumnCheck):
    def __init__(self, column_name: str, function: Callable[[Any], bool], description: str = "", raise_on_fail: bool = True, not_null: bool = False):
        super().__init__(column_name, raise_on_fail, not_null)
        self.function = function
        self.description = description or "Custom function check"

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()
        
        if self.not_null:
            null_mask = series.isna()
            if null_mask.any():
                messages.append(f"Column '{self.column_name}' contains missing values.")
                failing_indices.update(series[null_mask].index)

        invalid = ~series.map(self.function, na_action='ignore')

        if invalid.any():
            sample = list(series[invalid].unique()[:3])
            messages.append(
                f"{self.description} failed on column '{self.column_name}' for values: {sample}."
            )
            failing_indices.update(series[invalid].index)

        return {"messages": messages, "failing_indices": failing_indices}

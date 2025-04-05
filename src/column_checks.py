from datetime import datetime, timedelta
from decimal import Decimal
import numbers
import numpy as np
import pandas as pd
from typing import Any, Callable, List, Optional, Union


class ColumnCheck:
    def __init__(self, column_name: str, raise_on_fail: bool = True):
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail

    def validate(self, series: pd.Series) -> dict:
        raise NotImplementedError("Subclasses should implement validate()")


class ColumnExistsCheck(ColumnCheck):
    def validate(self, series: pd.Series) -> dict:
        return {"messages": [], "failing_indices": set()}  # pragma: no cover


class BoolColumnCheck(ColumnCheck):
    def validate(self, series: pd.Series) -> dict:
        messages = []
        invalid_values = series[~series.map(lambda x: isinstance(x, bool)) & series.notna()]
        failing_indices = set(invalid_values.index)
        if not invalid_values.empty:
            sample = list(invalid_values.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains non-boolean values: {sample}."
            )
        return {"messages": messages, "failing_indices": failing_indices}


class DatetimeColumnCheck(ColumnCheck):
    def __init__(
        self,
        column_name: str,
        min: Optional[str] = None,
        max: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        format: Optional[str] = None,
        raise_on_fail: bool = True
    ):
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail
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

        self.min = pd.to_datetime(min) if min else None
        self.max = pd.to_datetime(max) if max else None
        self.before = resolve_bound(before, "before")
        self.after = resolve_bound(after, "after")

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

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

        bounds = [
            ('min', self.min, lambda x: x < self.min),
            ('max', self.max, lambda x: x > self.max),
            ('before', self.before, lambda x: x >= self.before),
            ('after', self.after, lambda x: x <= self.after),
        ]

        for label, bound, condition in bounds:
            if bound is not None:
                mask = condition(coerced) | invalid_mask
                if mask.any():
                    bound_label = bound.date() if hasattr(bound, "date") else bound
                    messages.append(f"Column '{self.column_name}' violates '{label}' constraint: {bound_label}.")
                    failing_indices.update(series[mask].index)

        return {"messages": messages, "failing_indices": failing_indices}


class FloatColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, min: Optional[float] = None, max: Optional[float] = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.min = min
        self.max = max

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

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


class IntColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, min: Optional[int] = None, max: Optional[int] = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.min = min
        self.max = max

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

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
        if not invalid.empty:
            sample = list(invalid.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains values that are not integer-like (e.g., decimals or strings): {sample}."
            )
            failing_indices.update(invalid.index)

        if invalid.index.equals(series.dropna().index):
            return {"messages": messages, "failing_indices": failing_indices}

        valid_series = series.drop(index=invalid.index)

        inf_mask = valid_series.map(lambda x: isinstance(x, float) and np.isinf(x))
        if inf_mask.any():
            messages.append(f"Column '{self.column_name}' contains infinite values.")
            failing_indices.update(valid_series[inf_mask].index)

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

        return {"messages": messages, "failing_indices": failing_indices}


class StringColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, regex: Optional[str] = None, in_set: Optional[List[str]] = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.regex = regex
        self.in_set = in_set

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

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
            invalid_values = series[~series.isin(self.in_set)].dropna()
            if not invalid_values.empty:
                sample = list(invalid_values.unique()[:3])
                messages.append(
                    f"Column '{self.column_name}' contains unexpected values: {sample}."
                )
                failing_indices.update(invalid_values.index)

        return {"messages": messages, "failing_indices": failing_indices}


class CustomFunctionCheck(ColumnCheck):
    def __init__(self, column_name: str, function: Callable[[Any], bool], description: str = "", raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.function = function
        self.description = description or "Custom function check"

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

        invalid = ~series.map(self.function, na_action='ignore')

        if invalid.any():
            sample = list(series[invalid].unique()[:3])
            messages.append(
                f"{self.description} failed on column '{self.column_name}' for values: {sample}."
            )
            failing_indices.update(series[invalid].index)

        return {"messages": messages, "failing_indices": failing_indices}

from decimal import Decimal
import numbers
import numpy as np
import pandas as pd
from typing import Any, Callable


class ColumnCheck:
    def __init__(self, column_name: str, raise_on_fail: bool = True):
        self.column_name = column_name
        self.raise_on_fail = raise_on_fail

    def validate(self, series: pd.Series) -> dict:
        raise NotImplementedError("Subclasses should implement validate()")
        
        
class ColumnExistsCheck(ColumnCheck):
    def validate(self, series: pd.Series) -> dict:
        return {"messages": [], "failing_indices": set()}


class BoolColumnCheck(ColumnCheck):
    def validate(self, series: pd.Series) -> dict:
        messages = []
        invalid_values = series[~series.isin([True, False]) & series.notna()]
        failing_indices = set(invalid_values.index)

        if not invalid_values.empty:
            sample = list(invalid_values.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains non-boolean values: {sample}."
            )

        return {"messages": messages, "failing_indices": failing_indices}


class DatetimeColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, min: str = None, max: str = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.min = pd.to_datetime(min) if min else None
        self.max = pd.to_datetime(max) if max else None

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

        coerced = pd.to_datetime(series, errors='coerce')
        invalid = series[coerced.isna() & series.notna()]

        if not invalid.empty:
            sample = list(invalid.unique()[:3])
            messages.append(
                f"Column '{self.column_name}' contains values that are not valid dates: {sample}."
            )
            failing_indices.update(invalid.index)

        # Perform value checks even if some values are invalid
        if self.min is not None:
            mask = coerced < self.min
            if mask.any():
                messages.append(f"Column '{self.column_name}' has dates before {self.min.date()}.")
                failing_indices.update(series[mask].index)

        if self.max is not None:
            mask = coerced > self.max
            if mask.any():
                messages.append(f"Column '{self.column_name}' has dates after {self.max.date()}.")
                failing_indices.update(series[mask].index)

        return {"messages": messages, "failing_indices": failing_indices}



class FloatColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, min: float = None, max: float = None, raise_on_fail: bool = True):
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

        # Always continue to value checks
        coerced = pd.to_numeric(series, errors='coerce')

        if self.min is not None:
            mask = coerced < self.min
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values less than {self.min}.")
                failing_indices.update(series[mask].index)

        if self.max is not None:
            mask = coerced > self.max
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values greater than {self.max}.")
                failing_indices.update(series[mask].index)

        return {"messages": messages, "failing_indices": failing_indices}



class IntColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, min: int = None, max: int = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.min = min
        self.max = max

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()
    
        def is_integer_like(x):
            if pd.isna(x):
                return True
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
    
        # Keep checking even if type issues exist
        coerced = pd.to_numeric(series, errors='coerce')
    
        if self.min is not None:
            mask = coerced < self.min
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values less than {self.min}.")
                failing_indices.update(series[mask].index)
    
        if self.max is not None:
            mask = coerced > self.max
            if mask.any():
                messages.append(f"Column '{self.column_name}' has values greater than {self.max}.")
                failing_indices.update(series[mask].index)
    
        return {"messages": messages, "failing_indices": failing_indices}


class StringColumnCheck(ColumnCheck):
    def __init__(self, column_name: str, regex: str = None, in_set: list[str] = None, raise_on_fail: bool = True):
        super().__init__(column_name, raise_on_fail)
        self.regex = regex
        self.in_set = in_set

    def validate(self, series: pd.Series) -> dict:
        messages = []
        failing_indices = set()

        if self.regex:
            failed = series.astype(str)[~series.astype(str).str.match(self.regex, na=False)]
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


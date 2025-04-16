# dataframe_checks.py
import pandas as pd
from typing import Optional, List, Dict, Set


class DataFrameCheck:
    def __init__(self, raise_on_fail: bool = True):
        self.raise_on_fail = raise_on_fail

    def validate(self, df: pd.DataFrame) -> Dict[str, object]:
        raise NotImplementedError("Subclasses must implement validate()")


class CustomCheck(DataFrameCheck):
    def __init__(self, function, description: Optional[str] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.function = function
        self.description = description or "Custom check failed"

    def validate(self, df: pd.DataFrame) -> dict:
        messages = []
        failing_indices = set()

        invalid_mask = ~df.apply(self.function, axis=1)
        if invalid_mask.any():
            failing_indices = df[invalid_mask].index
            messages.append(f"{self.description} (failed on {len(failing_indices)} row(s))")

        return {"messages": messages, "failing_indices": set(failing_indices)}


class DefinedColumnsOnlyCheck(DataFrameCheck):
    def __init__(self, expected_columns: List[str], raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.expected_columns = set(expected_columns)

    def validate(self, df: pd.DataFrame) -> dict:
        actual = set(df.columns)
        extra = actual - self.expected_columns
        messages = []
        if extra:
            messages.append(f"Unexpected columns in DataFrame: {sorted(extra)}")
        return {"messages": messages, "failing_indices": set()}


class ExactColumnsCheck(DataFrameCheck):
    def __init__(self, expected_columns: List[str], raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.expected_columns = expected_columns

    def validate(self, df: pd.DataFrame) -> dict:
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
    def __init__(self, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)

    def validate(self, df: pd.DataFrame) -> dict:
        messages = []
        if df.empty:
            messages.append("DataFrame is unexpectedly empty.")
        return {"messages": messages, "failing_indices": set()}


class IsEmptyCheck(DataFrameCheck):
    def __init__(self, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)

    def validate(self, df: pd.DataFrame) -> dict:
        messages = []
        if not df.empty:
            messages.append("DataFrame is unexpectedly non-empty.")
        return {"messages": messages, "failing_indices": set()}


class NoNullsCheck(DataFrameCheck):
    def __init__(self, columns: Optional[List[str]] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.columns = columns

    def validate(self, df: pd.DataFrame) -> dict:
        cols_to_check = self.columns or df.columns.tolist()
        messages = []
        failing_indices = set()

        for col in cols_to_check:
            if df[col].isna().any():
                messages.append(f"Column '{col}' contains null values.")
                failing_indices.update(df[df[col].isna()].index)

        return {"messages": messages, "failing_indices": failing_indices}


class UniquenessCheck(DataFrameCheck):
    def __init__(self, columns: Optional[List[str]] = None, raise_on_fail: bool = True):
        super().__init__(raise_on_fail)
        self.columns = columns

    def validate(self, df: pd.DataFrame) -> Dict[str, object]:
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

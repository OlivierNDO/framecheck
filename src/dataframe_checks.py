# dataframe_checks.py
import pandas as pd
from typing import Optional, List, Dict, Set


class DataFrameCheck:
    def __init__(self, raise_on_fail: bool = True):
        self.raise_on_fail = raise_on_fail

    def validate(self, df: pd.DataFrame) -> Dict[str, object]:
        raise NotImplementedError("Subclasses must implement validate()")


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


class DefinedColumnsOnlyCheck:
    def __init__(self, expected_columns: List[str], raise_on_fail: bool = True):
        self.expected_columns = set(expected_columns)
        self.raise_on_fail = raise_on_fail

    def validate(self, df: pd.DataFrame) -> dict:
        actual = set(df.columns)
        extra = actual - self.expected_columns
        messages = []
        if extra:
            messages.append(f"Unexpected columns in DataFrame: {sorted(extra)}")
        return {"messages": messages, "failing_indices": set()}

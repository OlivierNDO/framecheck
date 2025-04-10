import pandas as pd
from typing import Union, List, Set, Optional, Dict, Any

from .column_checks import (
    IntColumnCheck,
    FloatColumnCheck,
    StringColumnCheck,
    BoolColumnCheck,
    DatetimeColumnCheck,
    CustomFunctionCheck,
    ColumnExistsCheck
)

from .dataframe_checks import (
    DataFrameCheck,
    UniquenessCheck,
    DefinedColumnsOnlyCheck,
    IsEmptyCheck,
    NotEmptyCheck
    
)

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
        warnings = []
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
                (errors if check.raise_on_fail else warnings).append(msg)
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
                    warnings.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        # DataFrame-level checks
        for df_check in self.dataframe_checks:
            result = df_check.validate(df)
            if result.get("messages"):
                if df_check.raise_on_fail:
                    errors.extend(result["messages"])
                    error_indices.update(result["failing_indices"])
                else:
                    warnings.extend(result["messages"])
                failing_indices.update(result["failing_indices"])

        result = ValidationResult(errors=errors, warnings=warnings, failing_row_indices=failing_indices)
        result._error_indices = error_indices
        return result



class FrameCheck:
    def __init__(self):
        self._column_checks = []
        self._dataframe_checks = []
        self._finalized = False

    def only_defined_columns(self) -> 'FrameCheck':
        self._finalized = True
        return self

    def column(self, name: str, **kwargs) -> 'FrameCheck':
        if self._finalized:
            raise RuntimeError("Cannot call .column() after .only_defined_columns() — move column definitions above.")
        col_type = kwargs.pop('type', None)
        raise_on_fail = not kwargs.pop('warn_only', False)

        if col_type is None and 'regex' not in kwargs and 'in_set' not in kwargs and 'function' not in kwargs:
            self._column_checks.append(ColumnExistsCheck(name, raise_on_fail))
            return self

        if col_type == 'int':
            self._column_checks.append(IntColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'float':
            self._column_checks.append(FloatColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'bool':
            self._column_checks.append(BoolColumnCheck(
                column_name=name,
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'datetime':
            self._column_checks.append(DatetimeColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                before=kwargs.get('before'),
                after=kwargs.get('after'),
                format=kwargs.get('format'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'string':
            self._column_checks.append(StringColumnCheck(
                column_name=name,
                regex=kwargs.get('regex'),
                in_set=kwargs.get('in_set'),
                raise_on_fail=raise_on_fail
            ))

        elif 'function' in kwargs:
            self._column_checks.append(CustomFunctionCheck(
                column_name=name,
                function=kwargs['function'],
                description=kwargs.get('description', ''),
                raise_on_fail=raise_on_fail
            ))

        return self
    
    def columns(self, names: List[str], **kwargs) -> 'FrameCheck':
        for name in names:
            self.column(name, **kwargs)
        return self


    def unique(self, columns: Optional[List[str]] = None) -> 'FrameCheck':
        self._dataframe_checks.append(UniquenessCheck(columns=columns))
        return self
    
    def empty(self) -> 'FrameCheck':
        self._dataframe_checks.append(IsEmptyCheck())
        return self

    def not_empty(self) -> 'FrameCheck':
        self._dataframe_checks.append(NotEmptyCheck())
        return self
    

    def build(self) -> Schema:
        if self._finalized:
            expected_cols = [check.column_name for check in self._column_checks if hasattr(check, 'column_name')]
            self._dataframe_checks.append(DefinedColumnsOnlyCheck(expected_columns=expected_cols))
        return Schema(self._column_checks, self._dataframe_checks)

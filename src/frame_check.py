import pandas as pd

from .schema import (
    IntColumnCheck,
    FloatColumnCheck,
    StringColumnCheck,
    BoolColumnCheck,
    DatetimeColumnCheck,
    CustomFunctionCheck,
    ColumnExistsCheck
)


class ValidationResult:
    def __init__(self, errors: list[str], warnings: list[str], failing_row_indices: set[int] = None):
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


    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }



class Schema:
    def __init__(self, checks: list, disallow_extra_columns: bool = False):
        self.checks = checks
        self.disallow_extra_columns = disallow_extra_columns

    def validate(self, df) -> ValidationResult:
        errors = []
        warnings = []
        failing_indices = set()
        error_indices = set()

        for check in self.checks:
            if check.column_name not in df.columns:
                msg = (
                    f"Column '{check.column_name}' is missing."
                    if check.__class__.__name__ == "ColumnExistsCheck"
                    else f"Column '{check.column_name}' does not exist in DataFrame."
                )
                (errors if check.raise_on_fail else warnings).append(msg)
                continue

            series = df[check.column_name]
            result = check.validate(series)
            if not isinstance(result, dict):
                raise TypeError(f"Validation check for column '{check.column_name}' did not return a dict. Got: {type(result)}")

            messages = result.get("messages", [])
            indices = result.get("failing_indices", [])

            if messages:
                if check.raise_on_fail:
                    errors.extend(messages)
                    error_indices.update(indices)  # ✅ Track error-only row indices
                else:
                    warnings.extend(messages)

            failing_indices.update(indices)

        print("Errors content:", errors)
        print("Warnings content:", warnings)

        result = ValidationResult(errors=errors, warnings=warnings, failing_row_indices=failing_indices)
        result._error_indices = error_indices  # ✅ Attach for downstream access
        return result



class FrameCheck:
    def __init__(self):
        self._checks = []
        self._disallow_extra_columns = False

    def only_defined_columns(self):
        self._disallow_extra_columns = True
        self._finalized = True
        return self

    def column(self, name: str, **kwargs):
        if getattr(self, '_finalized', False):
            raise RuntimeError("Cannot call .column() after .only_defined_columns() — move column definitions above.")
        col_type = kwargs.pop('type', None)
        raise_on_fail = not kwargs.pop('warn_only', False)

        if col_type is None and 'regex' not in kwargs and 'in_set' not in kwargs and 'function' not in kwargs:
            self._checks.append(ColumnExistsCheck(name, raise_on_fail))
            return self

        if col_type == 'int':
            self._checks.append(IntColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'float':
            self._checks.append(FloatColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'bool':
            self._checks.append(BoolColumnCheck(
                column_name=name,
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'datetime':
            self._checks.append(DatetimeColumnCheck(
                column_name=name,
                min=kwargs.get('min'),
                max=kwargs.get('max'),
                raise_on_fail=raise_on_fail
            ))

        elif col_type == 'string':
            self._checks.append(StringColumnCheck(
                column_name=name,
                regex=kwargs.get('regex'),
                in_set=kwargs.get('in_set'),
                raise_on_fail=raise_on_fail
            ))

        elif 'function' in kwargs:
            self._checks.append(CustomFunctionCheck(
                column_name=name,
                function=kwargs['function'],
                description=kwargs.get('description', ''),
                raise_on_fail=raise_on_fail
            ))

        return self

    def build(self):
        return Schema(self._checks, disallow_extra_columns=self._disallow_extra_columns)

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
    def __init__(self, errors: list[str], warnings: list[str]):
        self.errors = errors
        self.warnings = warnings

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

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

        if self.disallow_extra_columns:
            expected = {check.column_name for check in self.checks}
            actual = set(df.columns)
            extra = actual - expected
            if extra:
                errors.append(f"Unexpected columns in DataFrame: {sorted(extra)}")

        for check in self.checks:
            if check.column_name not in df.columns:
                if check.__class__.__name__ == "ColumnExistsCheck":
                    msg = f"Column '{check.column_name}' is missing."
                else:
                    msg = f"Column '{check.column_name}' does not exist in DataFrame."

                (errors if check.raise_on_fail else warnings).append(msg)
                continue

            series = df[check.column_name]
            result = check.validate(series)

            if result:
                target = errors if check.raise_on_fail else warnings
                target.extend(result)

        return ValidationResult(errors=errors, warnings=warnings)


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

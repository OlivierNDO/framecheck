# <img src="images/logo.png" alt="Project Logo" width="512" height="125">

[![codecov](https://codecov.io/gh/OlivierNDO/framecheck/branch/main/graph/badge.svg)](https://codecov.io/gh/OlivierNDO/framecheck)


**Lightweight, flexible, and intuitive validation for pandas DataFrames.**  
Define expectations for your data, validate them cleanly, and surface friendly errors or warnings — no configuration files, ever.

---

## 📦 Installation

```bash
pip install framecheck
```

---

## Main Features

- Designed for pandas users  
- Simple, fluent API  
- Supports error **or** warning-level assertions  
- Validates both column-level and DataFrame-level rules  
- No config files, decorators, or boilerplate  


---

## Table of Contents

- [Getting Started](#example-catch-bad-model-output-before-it-hits-production)
- [Comparison with Other Approaches](#comparison-with-other-approaches)
  - [pydantic](#equivalent-code-in-pydantic)
- [FrameCheck Methods](#framecheck-methods)
  - [.column(...)](#column--core-behaviors)
  - [.columns(...)](#columns)
  - [.columns_are(...)](#columns_are--exact-column-names-and-order)
  - [.custom_check(...)](#custom_check)
  - [.empty()](#empty--ensure-the-dataframe-is-empty)
  - [.not_empty()](#not_empty--ensure-the-dataframe-is-not-empty)
  - [.only_defined_columns()](#only_defined_columns--no-extraunexpected-columns-allowed)
  - [.row_count(...)](#row_count--validate-the-number-of-rows)
  - [.unique(...)](#unique--rows-must-be-unique)
- [Validation Results](#validation-results)
  - [.validate()](#validate--run-all-checks-and-collect-results)
  - [.get_invalid_rows(...)](#get_invalid_rows--return-subset-of-failing-rows)
- [License](#license)
- [Contact](#contact)


---


## 🔥 Example: Catch Bad Model Output Before It Hits Production
Model output that gets sent to a production application:
```python
import logging
import pandas as pd
from framecheck import FrameCheck

logger = logging.getLogger("model_validation")
logger.setLevel(logging.INFO)

df = pd.DataFrame({
    'transaction_id': ['TXN1001', 'TXN1002', 'TXN1003'],
    'user_id': [501, 502, 503],
    'transaction_time': ['2024-04-15 08:23:11', '2024-04-15 08:45:22', '2024-04-15 09:01:37'],
    'model_score': [0.03, 0.92, 0.95],
    'model_version': ['v2.1.0', 'v2.1.0', 'v2.1.0'],
    'flagged_for_review': [False, True, False]
})
```

Before it goes downstream, this data **must** meet these conditions:

- transaction_id follows a TXN format
- user_id is a positive integer
- transaction_time is a datetime before now
- model_score is a float between 0.0 and 1.0
- model_version looks like a version string (e.g. v2.1.0)
- flagged_for_review is boolean
- no missing values anywhere
- no extra columns
- DataFrame is not empty
- And: if model_score > 0.9, it must be flagged for review

We would like a **warning** if:
- model_score is exactly zero.

If any of these criteria are not met, we need to:
- Log the warnings and log (or raise exceptions for) errors
- Record which records have invalid data


With FrameCheck:
```python
model_output_validator = (
    FrameCheck()
    .column('transaction_id', type='string', regex=r'^TXN\d{4,}$')
    .column('user_id', type='int', min=1)
    .column('transaction_time', type='datetime', before='now')
    .column('model_score', type='float', min=0.0, max=1.0)
    .column('model_score', type='float', not_in_set=[0.0], warn_only=True)
    .column('model_version', type='string')
    .column('flagged_for_review', type='bool')
    .custom_check(
        lambda row: row['model_score'] <= 0.9 or row['flagged_for_review'] is True,
        "flagged_for_review must be True when model_score > 0.9"
    )
    .not_null()
    .not_empty()
    .only_defined_columns()
)

result = model_output_validator.validate(df)

if not result.is_valid:
    invalid_rows = result.get_invalid_rows(df)
    summary = result.summary()
```

Without framecheck, this would be **a lot** of code. Now you can...


View or save records with errors:
```python
invalid_rows = result.get_invalid_rows(df) # optionally include warning rows with `include_warnings = True`
print(invalid_rows)
```

| transaction_id | user_id | transaction_time     | model_score | model_version | flagged_for_review |
|----------------|---------|----------------------|-------------|----------------|---------------------|
| TXN1003        | 503     | 2024-04-15 09:01:37  | 0.95        | v2.1.0         | False               |


Print a summary:
```python
print(result.summary())
```

```bash
Validation FAILED
1 error(s), 1 warning(s)
Errors:
  - flagged_for_review must be True when model_score > 0.9 (failed on 1 row(s))
Warnings:
  - Column 'model_score' contains disallowed values: [0.0].
```


Log warning(s):
```python
if result.warnings:
    logger.warning("FrameCheck warnings:\n" + "\n".join(result.warnings))
```

```bash
FrameCheck warnings:
Column 'model_score' contains disallowed values: [0.0].
```


Log error(s):
```python
if not result.is_valid:
    logger.error("FrameCheck errors:\n" + "\n".join(result.errors))
    invalid_rows.to_csv("invalid_model_output.csv", index=False)
```

```bash
FrameCheck errors:
flagged_for_review must be True when model_score > 0.9 (failed on 1 row(s))
```

## Equivalent code in [pydantic](https://github.com/pydantic/pydantic)

Pydantic is a fantastic validation package with strong typing support and a much broader scope than just pandas DataFrames. It offers many more features than `framecheck`, but if you're optimizing for brevity and clarity, `framecheck` might be a better fit.

🧮 90+ lines → 19 with `FrameCheck`

Here's how you could implement the same validation logic using Pydantic’s model-based approach:


```python
from pydantic import BaseModel, Field, field_validator, model_validator

df['transaction_time'] = pd.to_datetime(df['transaction_time'])

class ModelOutput(BaseModel):
    transaction_id: str
    user_id: int
    transaction_time: datetime
    model_score: float
    model_version: str
    flagged_for_review: bool
    
    expected_columns: ClassVar[set] = {'transaction_id', 'user_id', 'transaction_time', 
                                      'model_score', 'model_version', 'flagged_for_review'}
    
    @field_validator('transaction_id')
    @classmethod
    def transaction_id_format(cls, v):
        if not re.match(r'^TXN\d{4,}$', v):
            raise ValueError(f"transaction_id must follow TXN format, got: {v}")
        return v
    
    @field_validator('user_id')
    @classmethod
    def user_id_positive(cls, v):
        if v < 1:
            raise ValueError("user_id must be positive")
        return v
    
    @field_validator('transaction_time')
    @classmethod
    def transaction_time_before_now(cls, v):
        if v > datetime.now():
            raise ValueError("transaction_time must be before now")
        return v
    
    @field_validator('model_score')
    @classmethod
    def model_score_range(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("model_score must be between 0.0 and 1.0")
        
        # Warning if model_score is exactly zero
        if v == 0.0:
            logger.warning("WARNING: model_score is exactly zero")
        
        return v
    
    @field_validator('model_version')
    @classmethod
    def model_version_format(cls, v):
        if not re.match(r'^v\d+\.\d+\.\d+$', v):
            raise ValueError("model_version must look like a version string (e.g., v2.1.0)")
        return v
    
    @model_validator(mode='after')
    def high_score_must_be_flagged(self):
        if self.model_score > 0.9 and not self.flagged_for_review:
            raise ValueError("flagged_for_review must be True when model_score > 0.9")
        return self
    
    @classmethod
    def validate_dataframe(cls, df):
        errors = []
        warnings = []
        
        if df.empty:
            errors.append("DataFrame is empty")
            return errors, warnings
        
        actual_columns = set(df.columns)
        if actual_columns != cls.expected_columns:
            extra_cols = actual_columns - cls.expected_columns
            missing_cols = cls.expected_columns - actual_columns
            if extra_cols:
                errors.append(f"Extra columns found: {extra_cols}")
            if missing_cols:
                errors.append(f"Missing columns: {missing_cols}")
        
        null_counts = df.isnull().sum()
        columns_with_nulls = null_counts[null_counts > 0].index.tolist()
        if columns_with_nulls:
            for col in columns_with_nulls:
                errors.append(f"Column '{col}' contains null values")
        
        for idx, row in df.iterrows():
            try:
                cls.model_validate(row.to_dict())
            except ValueError as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        return errors, warnings

errors, warnings = ModelOutput.validate_dataframe(df)

if not errors:
    print("All validation checks passed!")
else:
    print(f"Found {len(errors)} validation errors:")
    for error in errors:
        print(f"ERROR: {error}")
        logger.error(error)

if warnings:
    print(f"Found {len(warnings)} warnings:")
    for warning in warnings:
        print(f"WARNING: {warning}")
        logger.warning(warning)
```


---

## FrameCheck Methods  
```python
import pandas as pd
from framecheck import FrameCheck
```

### column(...) – Core Behaviors

#### ✅ Ensures column exists
```python
df = pd.DataFrame({'x': [1, 2, 3]})

schema = FrameCheck().column('x')
result = schema.validate(df)
```

```bash
FrameCheck validation passed.
```

#### ✅ Type enforcement
```python
df = pd.DataFrame({'x': [1, 2, 'bad']})

schema = FrameCheck().column('x', type='int')
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'x' contains values that are not integer-like (e.g., decimals or strings): ['bad'].
```

---

#### `.column(..., in_set=...)` – Allowed values
```python
df = pd.DataFrame({'status': ['new', 'active', 'archived']})

schema = FrameCheck().column('status', in_set=['new', 'active'])
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'status' contains values not in allowed set: ['archived'].
```

---

#### `.column(..., equals=...)` – All values must equal one thing
```python
df = pd.DataFrame({'is_active': [True, False, True]})

schema = FrameCheck().column('is_active', type='bool', equals=True)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'is_active' must equal True, but found values: [False].
```

---

#### `.column(..., not_null=...)` – All values non-null if set to True
```python
df = pd.DataFrame({'is_active': [True, False, None]})

schema = FrameCheck().column('is_active', type='bool', not_null=True)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'is_active' contains missing values.
  result = schema.validate(df)
```


---

#### `.column(..., regex=...)` – Pattern matching (for strings)
```python
df = pd.DataFrame({'email': ['x@example.com', 'bademail']})

schema = FrameCheck().column('email', type='string', regex=r'.+@.+\..+')
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'email' has values not matching regex '.+@.+\..+': ['bademail'].
```


#### `.column(..., min=..., max=..., after=..., before=...)` – Range & bound checks

```python
df = pd.DataFrame({
    'age': [25, 17, 101],
    'score': [0.9, 0.5, 1.2],
    'signup_date': ['2021-01-01', '2019-12-31', '2023-05-01'],
    'last_login': ['2020-01-01', '2026-01-01', '2023-06-15']
})

schema = (
    FrameCheck()
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=1.0)
    .column('signup_date', type='datetime', after='2020-01-01', before='2025-01-01')
    .column('last_login', type='datetime', min='2020-01-01', max='2025-01-01')
)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'age' has values less than 18.
- Column 'age' has values greater than 99.
- Column 'score' has values greater than 1.0.
- Column 'signup_date' violates 'after' constraint: 2020-01-01.
- Column 'last_login' violates 'max' constraint: 2025-01-01.
```


### columns(...)

Any .column() operation can be applied to multiple columns of the same type.

```python
df = pd.DataFrame({
    'a': [0, 1, 2],
    'b': [1, 0, 3],
    'c': [1, 1, 1]
})

schema = (
    FrameCheck()
    .columns(['a', 'b'], type='int', in_set=[0, 1])
)

result = schema.validate(df)
```

```bash
FrameCheck validation errors:
- Column 'a' contains values not in allowed set: [2].
- Column 'b' contains values not in allowed set: [3].
```


### columns_are(...) – Exact column names and order

```python
df = pd.DataFrame({'b': [1], 'a': [2]})

schema = FrameCheck().columns_are(['a', 'b'])
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

Expected columns in order: ['a', 'b']

Found columns in order: ['b', 'a']
```
[Go to Top](#main-features)

### custom_check(...)

```python
df = pd.DataFrame({
    'score': [0.2, 0.95, 0.6],
    'flagged': [False, False, True]
})

schema = (
FrameCheck()
.column('score', type='float')
.column('flagged', type='bool')
.custom_check(
    lambda row: row['score'] <= 0.9 or row['flagged'] is True,
    description="flagged must be True when score > 0.9"
)
)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

flagged must be True when score > 0.9 (failed on 1 row(s))
```


### empty() – Ensure the DataFrame is empty

```python
df = pd.DataFrame({'x': [1, 2]})

schema = FrameCheck().empty()
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

DataFrame is expected to be empty but contains rows.
```


### `.get_invalid_rows()` – Return subset of failing rows

Use `get_invalid_rows(df)` on the result of `.validate()` to extract only the rows that failed one or more checks.

```python
df = pd.DataFrame({
    'a': [1, 2, -1],
    'b': [10, 20, 30]
})

schema = FrameCheck().column('a', type='int', min=0)
result = schema.validate(df)

if not result.is_valid:
    invalid_df = result.get_invalid_rows(df)
    print(invalid_df)
```

```css
   a   b
2 -1  30
```

This is useful when you want to log, inspect, or export failing rows for debugging or downstream review.


### not_empty() – Ensure the DataFrame is not empty

```python
df = pd.DataFrame(columns=['a', 'b'])

schema = FrameCheck().not_empty()
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

DataFrame is unexpectedly empty.
```


### only_defined_columns() – No extra/unexpected columns allowed

```python
df = pd.DataFrame({'a': [1], 'b': [2], 'extra': [999]})

schema = (
FrameCheck()
.column('a')
.column('b')
.only_defined_columns()
)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

Unexpected columns in DataFrame: ['extra']
```


### row_count(...) – Validate the number of rows

✅ Minimum rows
```python
df = pd.DataFrame({'x': [1, 2]})

schema = FrameCheck().row_count(min=5)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

DataFrame must have at least 5 rows (found 2).
```

✅ Exact rows
```python
df = pd.DataFrame({'x': [1, 2, 3]})

schema = FrameCheck().row_count(exact=2)
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

DataFrame must have exactly 2 rows (found 3).
```


### unique(...) – Rows must be unique

✅ All rows must be entirely unique
```python
df = pd.DataFrame({
'user_id': [1, 2, 2],
'email': ['a@example.com', 'b@example.com', 'b@example.com']
})

schema = FrameCheck().unique()
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

Rows are not unique.
```

✅ Rows must be unique based on specific columns
```python
df = pd.DataFrame({
'user_id': [1, 2, 2],
'email': ['a@example.com', 'b@example.com', 'c@example.com']
})

schema = FrameCheck().unique(columns=['user_id'])
result = schema.validate(df)
```

```bash
FrameCheck validation errors:

Rows are not unique based on columns: ['user_id']
```

### `.validate()` – Run all checks and collect results

The `.validate()` method executes all column and DataFrame-level checks defined in your `FrameCheck` schema and returns a `ValidationResult` object.

```python
df = pd.DataFrame({
    'score': [0.1, 0.5, 1.2]  # 1.2 exceeds the max
})

schema = FrameCheck().column('score', type='float', max=1.0)
result = schema.validate(df)

if not result.is_valid:
    print(result.summary())
```

```sql
FrameCheck validation errors:
- Column 'score' has values greater than 1.0.
```




[Go to Top](#main-features)

---

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

<hr>

[Go to Top](#main-features)
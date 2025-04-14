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

- [Getting Started](#example-catch-data-issues-before-they-cause-bugs)
- [Output](#output)
- [Comparison with Other Approaches](#comparison-with-other-approaches)
  - [great_expectations](#equivalent-code-in-greatexpectations)
  - [Manual Validation](#equivalent-code-without-a-package)
- [FrameCheck Methods](#framecheck-methods)
  - [.column(...)](#column--core-behaviors)
  - [.columns(...)](#columns)
  - [.columns_are(...)](#columns_are---exact-column-names-and-order)
  - [.empty()](#empty---ensure-the-dataframe-is-empty)
  - [.not_empty()](#not_empty---ensure-the-dataframe-is-not-empty)
  - [.only_defined_columns()](#only_defined_columns---no-extraunexpected-columns-allowed)
  - [.row_count(...)](#row_count---validate-the-number-of-rows)
  - [.unique(...)](#unique---rows-must-be-unique)
- [License](#license)
- [Contact](#contact)



---


## 🔥 Example: Catch data issues before they cause bugs
Example dataframe:
```python
import pandas as pd
from framecheck import FrameCheck

df = pd.DataFrame({
    'a': [0, 1, 0, 1, 2],
    'b': [1, 1, 0, 0, 3],
    'timestamp': ['2022-01-01', '2022-01-02', '2019-12-31', '2021-01-01', '2023-05-01'],
    'email': ['a@example.com', 'bad', 'b@example.com', 'not-an-email', 'c@example.com'],
    'extra': ['x'] * 5
})
```

With FrameCheck:
```python
validator = (
    FrameCheck()
    .columns(['a', 'b'], type='int', in_set=[0, 1])
    .column('timestamp', type='datetime', after='2020-01-01')
    .column('email', type='string', regex=r'.+@.+\..+', warn_only=True)
    .only_defined_columns()
    .row_count(min=5, max=100)
    .not_empty()
    .raise_on_error()
)

result = validator.validate(df)
```

- `.warn_only=True` allows specific checks to issue warnings instead of failing validation.  
- `.raise_on_error()` makes the entire validation raise an exception if **any non-warning** failure occurs.  
- Together, they let you enforce hard rules while still being lenient on others.

For example, in the code above:  
- Invalid email formats will trigger a warning but not block execution.  
- Everything else (bad types, missing columns, out-of-bound values, etc.) will raise an error.

## 🧾 Output
If the data is invalid, you'll get warning ...
```sql
FrameCheckWarning: FrameCheck validation warnings:
- Column 'email' has values not matching regex '.+@.+\..+': ['bad'].
  result = validator.validate(df)
```

... and because you used .raise_on_error(), it'll raise a clean exception:
```sql
ValueError: FrameCheck validation failed:
Column 'a' is missing.
Column 'b' is missing.
Column 'timestamp' is missing.
DataFrame must have at least 5 rows (found 3).
Unexpected columns in DataFrame: ['good_credit', 'home_owner', 'id', 'promo_eligible', 'score']
```

---

## Comparison with Other Approaches

Equivalent code in [great_expectations](https://docs.greatexpectations.io/)
(which is a fantastic package with a much broader focus than FrameCheck).


```python
import great_expectations as ge

ge_df = ge.from_pandas(df)
ge_df.expect_column_values_to_be_in_set('a', [0, 1])
ge_df.expect_column_values_to_be_of_type('a', 'int64')
ge_df.expect_column_values_to_be_in_set('b', [0, 1])
ge_df.expect_column_values_to_be_of_type('b', 'int64')
ge_df['timestamp'] = pd.to_datetime(ge_df['timestamp'])
ge_df.expect_column_values_to_be_of_type('timestamp', 'datetime64[ns]')
ge_df.expect_column_values_to_be_between('timestamp', min_value='2020-01-01')
ge_df.expect_column_values_to_match_regex('email', r'.+@.+\..+', mostly=1.0)
ge_df.expect_table_row_count_to_be_between(min_value=5, max_value=100)
ge_df.expect_table_row_count_to_be_greater_than(0)
expected_columns = {'a', 'b', 'timestamp', 'email'}
unexpected = set(df.columns) - expected_columns
if unexpected:
    raise ValueError(f"Unexpected columns in DataFrame: {unexpected}")

results = ge_df.validate()
if not results['success']:
    raise ValueError(f"Validation failed: {results}")
```

Equivalent code without a package:

```python
import pandas as pd
import re

errors = []

if df.empty:
    errors.append("DataFrame is empty.")

row_count = len(df)
if row_count < 5:
    errors.append("DataFrame has fewer than 5 rows.")
if row_count > 100:
    errors.append("DataFrame has more than 100 rows.")

for col in ['a', 'b']:
    if col not in df.columns:
        errors.append(f"Missing column: {col}")
    else:
        if not pd.api.types.is_integer_dtype(df[col]):
            errors.append(f"Column '{col}' is not of integer type.")
        if not df[col].isin([0, 1]).all():
            errors.append(f"Column '{col}' contains values outside [0, 1].")

if 'timestamp' not in df.columns:
    errors.append("Missing column: 'timestamp'")
else:
    try:
        ts = pd.to_datetime(df['timestamp'], errors='coerce')
        if ts.isna().any():
            errors.append("Column 'timestamp' contains non-datetime values.")
        elif (ts < pd.Timestamp('2020-01-01')).any():
            errors.append("Column 'timestamp' has values before 2020-01-01.")
    except Exception:
        errors.append("Could not convert 'timestamp' to datetime.")

if 'email' in df.columns:
    invalid_emails = df[~df['email'].astype(str).str.match(r'.+@.+\..+')]
    if not invalid_emails.empty:
        print("Warning: Some emails don't match expected pattern.")

expected_cols = {'a', 'b', 'timestamp', 'email'}
actual_cols = set(df.columns)
unexpected = actual_cols - expected_cols
if unexpected:
    errors.append(f"Unexpected columns in DataFrame: {sorted(unexpected)}")

# Final decision
if errors:
    raise ValueError("Validation failed:\n" + "\n".join(errors))
```

---

## FrameCheck Methods  
```python
import pandas as pd
from framecheck import FrameCheck
```

### `.column(...)` – Core Behaviors

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


### `columns(...)`

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

### unique() – Rows must be unique

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


---

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

<hr>

[Go to Top](#main-features)
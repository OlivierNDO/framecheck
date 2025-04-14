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

- [Getting Started](#-example-catch-data-issues-before-they-cause-bugs)
- [Output](#-output)
- [Comparison with Other Approaches](#equivalent-code-in-greatexpectations)
    - [great_expectations](#equivalent-code-in-greatexpectations)
    - [Manual Validation](#equivalent-code-without-a-package)
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

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

<hr>

[Go to Top](#main-features)
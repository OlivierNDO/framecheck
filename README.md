# <img src="images/logo.png" alt="Project Logo" width="512" height="125">


**Lightweight, flexible, and intuitive validation for pandas DataFrames.**  
Define expectations for your data, validate them cleanly, and surface friendly errors or warnings — no configuration files, ever.

---

## Installation

pip install coming soon

---

## Main Features

- Designed for pandas users  
- Simple, fluent API  
- Supports error **or** warning-level assertions  
- Validates both column-level and DataFrame-level rules  
- No config files, decorators, or boilerplate  


---

## Table of Contents

- [Getting Started](#getting-started)
- [Core FrameCheck Features](#core-framecheck-features)
    - [column](#column)
    - [warn_only](#warn_only)
    - [only_defined_columns](#only_defined_columns)
    - [get_invalid_rows](#get_invalid_rows)
- [License](#license)


---

## Core FrameCheck Features

### single, mostly-comprehensive example of functionality
Defines expectations for individual columns—list any column you want to validate or ensure is present, even if no specific checks are applied.
```python
import pandas as pd
from framecheck import FrameCheck

df = pd.DataFrame({
    'id': ['a98325jh', '235lkjl25', '23543k5'],
    'age': [25, 18, 85.0],
    'score': [0.5, 0.9, 0.56],
    'subscribed': [True, False, True],
    'signup_date': pd.to_datetime(['2022-01-01', '2023-01-01', '2024-01-01']),
    'email': ['a@example.com', 'abc@gmail.com', 'b@example.com'],
    'phone': ['1231235757', '2828437222', '2139499999'],
    'extra_column': ['unexpected', 'should', 'flag']
})

validator = (
    FrameCheck()
    # Column presence + typed validation
    .column('id', type='string', regex=r'^[a-z0-9]+$')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=1.0)
    .column('subscribed', type='bool')
    .column('signup_date', type='datetime', after='2010-01-01', before='tomorrow')
    .column('email', type='string', regex=r'.+@.+\..+', in_set=['a@example.com', 'b@example.com'])
    .column('phone', function=lambda x: x.isdigit() and len(x) == 10, description="Phone must be 10 digits")
    
    # Check that this column exists, no further validation
    .column('missing_column')
    
    # Warn-only float max
    .column('score', type='float', max=0.6, warn_only=True)

    # DataFrame-level checks
    .only_defined_columns()  # Raise error if any unexpected columns
    .not_empty()             # Raise error if DataFrame is empty
    .unique(columns=['id'])  # Rows must be unique based on 'id'
    .build()
)

result = validator.validate(df)
```
There are a few things you can do with the result.

Print a summary:

```python
print(result.summary())
```

```bash
Validation FAILED
3 error(s), 1 warning(s)
Errors:
  - Column 'email' contains unexpected values: ['abc@gmail.com']
  - Column 'missing_column' is missing.
  - Unexpected columns in DataFrame: ['extra_column']
Warnings:
  - Column 'score' has values greater than 0.6.
```

Raise errors:
```python
if not result.is_valid:
    raise ValueError("Validation errors:\n" + "\n".join(result.errors))
```

```bash
ValueError: Validation errors:
Column 'email' contains unexpected values: ['abc@gmail.com'].
Column 'missing_column' is missing.
Unexpected columns in DataFrame: ['extra_column']
```

Log warnings:
```python
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if result.warnings:
    logger.warning("Validation warnings:\n" + "\n".join(result.warnings))
else:
    logger.info("DataFrame passed all checks.")
```

```bash
WARNING:__main__:Validation warnings:
Column 'score' has values greater than 0.6.
```




All examples below use the same DataFrame:

```python
import pandas as pd
from framecheck import FrameCheck

df = pd.DataFrame({
    'id': ['a98325jh', '235lkjl25', '23543k5'],
    'age': [25, 18, 85.0],
    'score': [0.5, 0.9, 0.56],
    'subscribed': [True, False, True],
    'signup_date': pd.to_datetime(['2022-01-01', '2023-01-01', '2024-01-01']),
    'email': ['a@example.com', 'abc@gmail.com', 'b@example.com'],
    'phone': ['1231235757', '2828437222', '2139499999']
})
```

---

### column
Defines expectations for individual columns—list any column you want to validate or ensure is present, even if no specific checks are applied.
```python
validator = (
    FrameCheck()
    .column('age', type='int', min=18, max=99)
    .column('email', type='string', regex=r'.+@.+\..+')
	.column('subscribed') # only checks if 'subscribed' exists
    .build()
)

result = validator.validate(df)
print(result.summary())
```

---

### warn_only
Marks a check to issue warnings instead of errors, allowing validation to pass even if the condition is violated.
```python
validator = (
    FrameCheck()
    .column('score', type='float', max=0.55, warn_only=True)
    .build()
)

result = validator.validate(df)
print(result.summary())
```

---

### only_defined_columns
Ensures the DataFrame contains **only** the explicitly defined columns and no extras.
```python
validator = (
    FrameCheck()
    .column('id')
    .column('email', type='string')
    .only_defined_columns()
    .build()
)

result = validator.validate(df)
print(result.summary())
```

---

### get_invalid_rows
Returns a new DataFrame containing rows that failed validation.  
You can choose whether to include warning-only rows:
```python
validator = (
    FrameCheck()
    .column('id')
    .column('email', type='string')
    .only_defined_columns()
    .build()
)

result = validator.validate(df)

# Include all failures (default)
invalid_df = result.get_invalid_rows(df)

# Only include rows with error-level failures
error_df = result.get_invalid_rows(df, include_warnings=False)
```

---

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

<hr>

[Go to Top](#main-features)
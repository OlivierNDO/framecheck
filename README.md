# framecheck

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

<hr>

[Go to Top](#main-features)
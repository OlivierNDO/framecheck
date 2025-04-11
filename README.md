# <img src="images/logo.png" alt="Project Logo" width="512" height="125">

[![codecov](https://codecov.io/gh/OlivierNDO/framecheck/branch/main/graph/badge.svg)](https://codecov.io/gh/OlivierNDO/framecheck)


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

## 🔥 Example: Catch data issues before they cause bugs

```python
import pandas as pd
from framecheck import FrameCheck

df = pd.DataFrame({
    'id': ['a123', 'b456', 'c789'],
    'age': [25, 17, 101],                   # too young, too old
    'good_credit': [0, 1, 0],
    'home_owner': [1, 1, 0],
    'promo_eligible': [0, 0, 1],
    'score': [0.9, 0.5, 1.2],               # 1.2 is out of bounds
    'email': ['x@example.com', 'bad', 'z@example.com'],  # invalid email
    'extra_column': ['extra', 'data', 'here']            # unexpected
})

validator = (
    FrameCheck()
    .columns(['good_credit', 'home_owner', 'promo_eligible'], type = 'int', in_set = [0, 1])
    .column('id', type='string', regex=r'^[a-z0-9]+$')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=1.0)
    .column('email', type='string', regex=r'.+@.+\..+', warn_only = True)

    # Also check: are there columns we didn't expect?
    .only_defined_columns()

    # Is the DataFrame empty?
    .not_empty()

    # Raise an exception if anything fails
    .raise_on_error()
)

# Validate!
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
Column 'age' has values less than 18.
Column 'age' has values greater than 99.
Column 'score' has values greater than 1.0.
Unexpected columns in DataFrame: ['extra_column']
...
```

---

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

<hr>

[Go to Top](#main-features)
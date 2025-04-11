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
Example dataframe:
```python
import pandas as pd
from framecheck import FrameCheck

df = pd.DataFrame({
    'id': ['a123', 'b456', 'c789'],
    'good_credit': [0, 1, 0],
    'home_owner': [1, 1, 0],
    'promo_eligible': [0, 0, 1],
    'score': [0.9, 0.5, 1.2],
    'email': ['x@example.com', 'bad', 'z@example.com'],
})
```

With FrameCheck:
```python
validator = (
    FrameCheck()
    .columns(['good_credit', 'home_owner', 'promo_eligible'], type = 'int', in_set = [0, 1])
    .column('score', type='float', min=0.0, max=1.0)
    .unique(columns = ['id'])
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
ValueError: FrameCheck validation failed: Column 'score' has values greater than 1.0.
```

Equivalent code without FrameCheck:
```python
errors = []

if df.empty:
    errors.append("DataFrame is empty.")

if df.duplicated(subset=['id']).any():
    errors.append("Duplicate values found in 'id'.")

for col in ['good_credit', 'home_owner', 'promo_eligible']:
    invalid = df[~df[col].isin([0, 1])]
    if not invalid.empty:
        errors.append(f"Column '{col}' contains values outside [0, 1].")

if (df['score'] < 0.0).any():
    errors.append("Column 'score' has values less than 0.0.")
if (df['score'] > 1.0).any():
    errors.append("Column 'score' has values greater than 1.0.")

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
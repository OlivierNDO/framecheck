
# <img src="images/logo.png" alt="Project Logo" width="512" height="125">

[![CI](https://github.com/OlivierNDO/framecheck/actions/workflows/coverage.yml/badge.svg)](https://github.com/OlivierNDO/framecheck/actions)
[![codecov](https://codecov.io/gh/OlivierNDO/framecheck/branch/main/graph/badge.svg)](https://codecov.io/gh/OlivierNDO/framecheck)
[![Documentation Status](https://readthedocs.org/projects/framecheck/badge/?version=latest)](https://framecheck.readthedocs.io/en/latest/)
![PyPI](https://img.shields.io/pypi/v/framecheck?cacheBust=3)
![Python](https://img.shields.io/badge/Python-3.8--3.12-blue?logo=python&logoColor=white)


**Lightweight, flexible, and intuitive validation for pandas DataFrames.**  
Define expectations for your data, validate them cleanly, and surface friendly errors or warnings — no configuration files, ever.

🔗 **[View full documentation →](https://framecheck.readthedocs.io/en/latest/)**

---

## 📦 Installation

```bash
pip install framecheck
```

---

## Try FrameCheck

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/OlivierNDO/framecheck/blob/main/framecheck_quickstart.ipynb)

Try FrameCheck without installing anything - click the badge above to run an interactive demo notebook in Google Colab.

---

## Main Features

- Designed for pandas users  
- Simple, fluent API  
- Supports error **or** warning-level assertions  
- Validates both column-level and DataFrame-level rules  
- No config files, decorators, or boilerplate  

---

## Why Should You Validate Your Data Explicitly?

Because during a routine update, a typo like this:

```sql
SELECT u.credit_score AS age
FROM users u
JOIN profiles p ON u.id = p.user_id
```
...fails silently.

Now your age column has values in the 700s.

Your SQL doesn't error, your model still runs — and makes terrible predictions.


---

## 🔥 Example: Catch Bad Model Output Before It Hits Production

```python
import pandas as pd
from framecheck import FrameCheck, register_check_function

df = pd.DataFrame({
    'transaction_id': ['TXN1001', 'TXN1002', 'TXN1003'],
    'user_id': [501, 502, 503],
    'transaction_time': ['2024-04-15 08:23:11', '2024-04-15 08:45:22', '2024-04-15 09:01:37'],
    'model_score': [0.03, 0.92, 0.95],
    'model_version': ['v2.1.0', 'v2.1.0', 'v2.1.0'],
    'flagged_for_review': [False, True, False]
})

@register_check_function(name="high_score_is_flagged")
def high_score_is_flagged(row):
    return row['model_score'] <= 0.9 or row['flagged_for_review'] is True

model_score_validator = (
    FrameCheck()
    .column('transaction_id', type='string', regex=r'^TXN\d{4,}$')
    .column('user_id', type='int', min=1)
    .column('transaction_time', type='datetime', before='now')
    .column('model_score', type='float', min=0.0, max=1.0)
    .column('model_score', type='float', not_in_set=[0.0], warn_only=True)
    .column('model_version', type='string')
    .column('flagged_for_review', type='bool')
    .custom_check(
        high_score_is_flagged,
        "flagged_for_review must be True when model_score > 0.9"
    )
    .not_null()
    .not_empty()
    .only_defined_columns()
)

result = model_score_validator.validate(df)

if not result.is_valid:
    print(result.summary())
```

**Output:**

```
Validation FAILED
1 error(s), 1 warning(s)
Errors:
  - flagged_for_review must be True when model_score > 0.9 (failed on 1 row(s))
Warnings:
  - Column 'model_score' contains disallowed values: [0.0].
```

**Identify Problem Records**
```python
invalid_rows = result.get_invalid_rows(df, include_warnings = True)
```

| transaction_id | user_id | transaction_time     | model_score | model_version | flagged_for_review |
|----------------|---------|----------------------|-------------|----------------|---------------------|
| TXN1003        | 503     | 2024-04-15 09:01:37  | 0.95        | v2.1.0         | False               |


## 📋 Save & Reuse Validation Rules
```python
model_score_validator.save('transaction_validator.json')

loaded_validator = FrameCheck.load('transaction_validator.json')

result = loaded_validator.validate(df)
```


---

## 📊 Comparison with Other Tools

FrameCheck is designed to be concise and pandas-native. For full comparisons with other packages:

- [Pydantic Comparison](https://framecheck.readthedocs.io/en/latest/usage_examples.html#validation-comparison)
- [Pandera Comparison](https://framecheck.readthedocs.io/en/latest/usage_examples.html#validation-comparison)

---

## License
MIT

---

## Contact
[![LinkedIn Badge](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oliviernicholas/)

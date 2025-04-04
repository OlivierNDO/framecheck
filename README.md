# framecheck

**Lightweight, flexible, and intuitive validation for pandas DataFrames.**  
Define expectations for your data, validate them cleanly, and surface friendly errors or warnings — all with zero configuration files.

---

## 📦 Installation

```bash
pip install framecheck
```

---

## 🧠 Why framecheck?

- Designed for pandas users
- Simple, fluent API
- Supports error **or** warning-level assertions
- Validates both column-level and DataFrame-level rules
- No config files, decorators, or boilerplate

---

## 📚 Table of Contents

- [Getting Started](#getting-started)
- [Defining Column Checks](#defining-column-checks)
- [Warnings vs Errors](#warnings-vs-errors)
- [Disallowing Extra Columns](#disallowing-extra-columns)

---

## 🚀 Getting Started

```python
from framecheck import FrameCheck

schema = (
    FrameCheck()
    .column('id')
    .column('score', type='float', min=0.0, max=1.0)
    .build()
)

result = schema.validate(df)
print(result.summary())
```

---

## ✅ Defining Column Checks

```python
FrameCheck()
    .column('age', type='int', min=18, max=99)
    .column('email', type='string', regex=r'.+@.+\..+')
    .build()
```

---

## ⚠️ Warnings vs Errors

```python
FrameCheck()
    .column('score', type='float', max=0.95, warn_only=True)
    .build()
```

Violations here won’t fail the schema, just raise a warning.

---

## 🔒 Disallowing Extra Columns

```python
FrameCheck()
    .column('id')
    .column('age', type='int')
    .only_defined_columns()
    .build()
```

Will raise an error if any unexpected columns are present in the DataFrame.

---

## 📬 Contributing

Coming soon! For now, feel free to open issues or suggestions.

---

## 📝 License

MIT

Usage Examples
==============

All examples assume you have:

.. code-block:: python

   import pandas as pd
   from framecheck import FrameCheck


column(...) – Core Behaviors
-----------------------------

Ensures column exists
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'x': [1, 2, 3]})
   schema = FrameCheck().column('x')
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation passed.

Type enforcement
^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'x': [1, 2, 'bad']})
   schema = FrameCheck().column('x', type='int')
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'x' contains values that are not integer-like (e.g., decimals or strings): ['bad'].

in_set: Allowed values
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'status': ['new', 'active', 'archived']})
   schema = FrameCheck().column('status', in_set=['new', 'active'])
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'status' contains values not in allowed set: ['archived'].

equals: All values must match
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'is_active': [True, False, True]})
   schema = FrameCheck().column('is_active', type='bool', equals=True)
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'is_active' must equal True, but found values: [False].

not_null=True: Non-null required
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'is_active': [True, False, None]})
   schema = FrameCheck().column('is_active', type='bool', not_null=True)
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'is_active' contains missing values.

regex: Pattern match
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'email': ['x@example.com', 'bademail']})
   schema = FrameCheck().column('email', type='string', regex=r'.+@.+\..+')
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'email' has values not matching regex '.+@.+\..+': ['bademail'].

Range & Bound Checks
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

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

.. code-block:: text

   FrameCheck validation errors:
   - Column 'age' has values less than 18.
   - Column 'age' has values greater than 99.
   - Column 'score' has values greater than 1.0.
   - Column 'signup_date' violates 'after' constraint: 2020-01-01.
   - Column 'last_login' violates 'max' constraint: 2025-01-01.


columns(...) and columns_are(...)
---------------------------------

Multiple column validation
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({
       'a': [0, 1, 2],
       'b': [1, 0, 3],
       'c': [1, 1, 1]
   })

   schema = FrameCheck().columns(['a', 'b'], type='int', in_set=[0, 1])
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   - Column 'a' contains values not in allowed set: [2].
   - Column 'b' contains values not in allowed set: [3].

Column order match
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'b': [1], 'a': [2]})
   schema = FrameCheck().columns_are(['a', 'b'])
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   Expected columns in order: ['a', 'b']
   Found columns in order: ['b', 'a']


custom_check(...)
-----------------

.. code-block:: python

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

.. code-block:: text

   FrameCheck validation errors:
   flagged must be True when score > 0.9 (failed on 1 row(s))


Other Checks
------------

empty()
^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'x': [1, 2]})
   schema = FrameCheck().empty()
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   DataFrame is expected to be empty but contains rows.

not_empty()
^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame(columns=['a', 'b'])
   schema = FrameCheck().not_empty()
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   DataFrame is unexpectedly empty.

only_defined_columns()
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'a': [1], 'b': [2], 'extra': [999]})
   schema = FrameCheck().column('a').column('b').only_defined_columns()
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   Unexpected columns in DataFrame: ['extra']

row_count()
^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({'x': [1, 2]})
   schema = FrameCheck().row_count(min=5)
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   DataFrame must have at least 5 rows (found 2).

unique(...)
^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({
       'user_id': [1, 2, 2],
       'email': ['a@example.com', 'b@example.com', 'b@example.com']
   })
   schema = FrameCheck().unique()
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   Rows are not unique.

Unique based on columns
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({
       'user_id': [1, 2, 2],
       'email': ['a@example.com', 'b@example.com', 'c@example.com']
   })
   schema = FrameCheck().unique(columns=['user_id'])
   result = schema.validate(df)

.. code-block:: text

   FrameCheck validation errors:
   Rows are not unique based on columns: ['user_id']

validate()
^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({
       'score': [0.1, 0.5, 1.2]  # 1.2 exceeds the max
   })

   schema = FrameCheck().column('score', type='float', max=1.0)
   result = schema.validate(df)

   if not result.is_valid:
       print(result.summary())

.. code-block:: text

   FrameCheck validation errors:
   - Column 'score' has values greater than 1.0.

get_invalid_rows()
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df = pd.DataFrame({
       'a': [1, 2, -1],
       'b': [10, 20, 30]
   })

   schema = FrameCheck().column('a', type='int', min=0)
   result = schema.validate(df)

   if not result.is_valid:
       invalid_df = result.get_invalid_rows(df)
       print(invalid_df)

.. code-block:: text

      a   b
   2 -1  30

This is useful when you want to log, inspect, or export failing rows for debugging or downstream review.


.. _validation_comparison:

Validation Comparison
=====================

This section compares how the same validation logic is expressed using three tools:

- **FrameCheck** (concise, purpose-built for DataFrames)
- **Pandera** (powerful, flexible, but not optimized for logging or row capture)
- **Pydantic** (designed for model schemas, not native to pandas)

---

Shared Setup
------------

.. code-block:: python

    import pandas as pd
    from datetime import datetime

    df = pd.DataFrame({
        'transaction_id': ['TXN1001', 'TXN1002', 'TXN1003', 'NUM9999'],
        'user_id': [501, 502, -1, 504],
        'transaction_time': ['2024-04-15 08:23:11', '2024-04-15 08:45:22', '2024-04-15 09:01:37', '2024-04-17 12:01:42'],
        'model_score': [0.03, 0.92, 0.95, 0.0],
        'model_version': ['v2.1.0', 'v2.1.0', 'v2.1.0', 'v2.1.0'],
        'flagged_for_review': [False, True, False, False]
    })

---

FrameCheck (19 lines)
---------------------

.. code-block:: python

    from framecheck import FrameCheck

    result = (
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
        .validate(df)
    )

    print(result.summary())

.. code-block:: text

    Validation FAILED
    3 error(s), 1 warning(s)
    Errors:
      - Column 'user_id' has values less than 1.
      - Column 'transaction_id' has values not matching regex '^TXN\d{4,}$'.
      - flagged_for_review must be True when model_score > 0.9 (failed on 1 row(s))
    Warnings:
      - Column 'model_score' contains disallowed values: [0.0].

---

Pandera (with row capture added manually)
-----------------------------------------

.. code-block:: python

    import pandera as pa
    from pandera import Column, Check, DataFrameSchema

    df['transaction_time'] = pd.to_datetime(df['transaction_time'])

    schema = DataFrameSchema({
        "transaction_id": Column(str, Check.str_matches(r"^TXN\d{4,}$"), nullable=False),
        "user_id": Column(int, Check.ge(1), nullable=False),
        "transaction_time": Column(pa.Timestamp, Check(lambda s: s < datetime.now()), nullable=False),
        "model_score": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "model_version": Column(str, nullable=False),
        "flagged_for_review": Column(bool, nullable=False),
    }, checks=[
        Check(
            lambda df: (df['model_score'] <= 0.9) | (df['flagged_for_review'] == True),
            element_wise=False,
            error="flagged_for_review must be True when model_score > 0.9"
        )
    ], strict=True)

    if df.empty:
        raise pa.errors.SchemaError("DataFrame is unexpectedly empty")

    if not df[df['model_score'] == 0.0].empty:
        print("Warning: model_score == 0.0 found")

    try:
        validated_df = schema.validate(df)
    except pa.errors.SchemaErrors as e:
        print("Pandera errors:")
        print(e.failure_cases[['column', 'failure_case', 'index']])

.. code-block:: text

    Warning: model_score == 0.0 found
    Pandera errors:
               column         failure_case  index
    0          user_id                  -1      2
    1    transaction_id            NUM9999      3
    2  flagged_for_review              NaN      2

---

Pydantic (manual row iteration)
-------------------------------

.. code-block:: python

    from pydantic import BaseModel, field_validator, model_validator
    from typing import ClassVar
    import re, logging

    logger = logging.getLogger()

    class ModelOutput(BaseModel):
        transaction_id: str
        user_id: int
        transaction_time: datetime
        model_score: float
        model_version: str
        flagged_for_review: bool

        expected_columns: ClassVar[set] = {
            'transaction_id', 'user_id', 'transaction_time',
            'model_score', 'model_version', 'flagged_for_review'
        }

        @field_validator('transaction_id')
        @classmethod
        def validate_txn(cls, v):
            if not re.match(r'^TXN\d{4,}$', v):
                raise ValueError("transaction_id must match TXN format")
            return v

        @field_validator('user_id')
        @classmethod
        def validate_uid(cls, v):
            if v < 1:
                raise ValueError("user_id must be positive")
            return v

        @field_validator('transaction_time')
        @classmethod
        def validate_time(cls, v):
            if v > datetime.now():
                raise ValueError("transaction_time must be before now")
            return v

        @field_validator('model_score')
        @classmethod
        def validate_score(cls, v):
            if not (0.0 <= v <= 1.0):
                raise ValueError("model_score must be in [0,1]")
            if v == 0.0:
                logger.warning("model_score == 0.0 found")
            return v

        @model_validator(mode='after')
        def check_flagged(self):
            if self.model_score > 0.9 and not self.flagged_for_review:
                raise ValueError("flagged_for_review must be True when score > 0.9")
            return self

        @classmethod
        def validate_df(cls, df):
            errors = []
            if df.empty:
                errors.append("DataFrame is empty")
            if set(df.columns) != cls.expected_columns:
                errors.append("Unexpected columns")
            for idx, row in df.iterrows():
                try:
                    cls.model_validate(row.to_dict())
                except Exception as e:
                    errors.append(f"Row {idx}: {e}")
            return errors

    errors = ModelOutput.validate_df(df)
    if errors:
        print("Pydantic validation errors:")
        for e in errors:
            print(e)

.. code-block:: text

    WARNING:root:model_score == 0.0 found
    Pydantic validation errors:
    Row 2: 1 validation error for ModelOutput
    __root__
      flagged_for_review must be True when score > 0.9 (type=value_error)
    Row 3: 1 validation error for ModelOutput
    transaction_id
      transaction_id must match TXN format (type=value_error)
    Row 2: 1 validation error for ModelOutput
    user_id
      user_id must be positive (type=value_error)

---

Conclusion
----------

FrameCheck achieves the same validations as Pandera and Pydantic with far less code and clearer intent. It also surfaces failing rows, warnings, and errors without additional plumbing.

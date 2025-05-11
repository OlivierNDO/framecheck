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

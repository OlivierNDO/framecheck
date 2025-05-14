FrameCheck Methods
==================
These methods allow you to declaratively define validation rules for pandas DataFrames.
Each method returns the FrameCheck instance to allow method chaining.

Basic DataFrame Checks
----------------------
.. autofunction:: framecheck.FrameCheck.empty
.. autofunction:: framecheck.FrameCheck.not_empty
.. autofunction:: framecheck.FrameCheck.not_null
.. autofunction:: framecheck.FrameCheck.only_defined_columns
.. autofunction:: framecheck.FrameCheck.raise_on_error

Row-Level Checks
----------------
.. autofunction:: framecheck.FrameCheck.row_count
.. autofunction:: framecheck.FrameCheck.unique

Column Checks
-------------
.. autofunction:: framecheck.FrameCheck.column
.. autofunction:: framecheck.FrameCheck.columns
.. autofunction:: framecheck.FrameCheck.columns_are

Cross-Column Validations
----------------------
.. autofunction:: framecheck.FrameCheck.compare

Custom Checks
-------------
.. autofunction:: framecheck.FrameCheck.custom_check

Validation Execution
--------------------
.. autofunction:: framecheck.FrameCheck.validate

Persistence
----------
.. autofunction:: framecheck.FrameCheck.export
.. autofunction:: framecheck.FrameCheck.to_json
.. autofunction:: framecheck.FrameCheck.to_dict
.. autofunction:: framecheck.FrameCheck.load
.. autofunction:: framecheck.FrameCheck.from_json
.. autofunction:: framecheck.FrameCheck.from_dict

Function Registry
----------------
.. autofunction:: framecheck.register_check_function
